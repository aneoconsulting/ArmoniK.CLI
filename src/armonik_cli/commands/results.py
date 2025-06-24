from collections import defaultdict
import logging
import pathlib
import grpc
import rich_click as click

from typing import IO, List, Optional, Union

from armonik.client.results import ArmoniKResults
from armonik.common import Result, Direction
from armonik.common.filter import PartitionFilter, Filter

from armonik_cli_core import console, base_command, base_group
from armonik_cli_core.configuration import CliConfig, create_grpc_channel
from armonik_cli_core.options import MutuallyExclusiveOption
from armonik_cli_core.params import FieldParam, FilterParam, ResultNameDataParam


@click.group(name="result")
@base_group
def results(**kwargs) -> None:
    """Manage results."""
    pass


@results.command(name="list")
@click.option(
    "-f",
    "--filter",
    "filter_with",
    type=FilterParam("Result"),
    required=False,
    help="An expression to filter the listed results with.",
    metavar="FILTER EXPR",
)
@click.option(
    "--sort-by",
    type=FieldParam("Result"),
    required=False,
    help="Attribute of result to sort with.",
)
@click.option(
    "--sort-direction",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    required=False,
    help="Whether to sort by ascending or by descending order.",
)
@click.option(
    "--page", default=-1, help="Get a specific page, it defaults to -1 which gets all pages."
)
@click.option("--page-size", default=100, help="Number of elements in each page")
@base_command(pass_config=True, auto_output="table")
def result_list(
    config: CliConfig,
    filter_with: Union[PartitionFilter, None],
    sort_by: Filter,
    sort_direction: str,
    page: int,
    page_size: int,
    **kwargs,
) -> None:
    """List the results of an ArmoniK cluster given <SESSION-ID>."""
    with create_grpc_channel(config) as channel:
        results_client = ArmoniKResults(channel)
        curr_page = page if page > 0 else 0
        results_list = []
        while True:
            total, results = results_client.list_results(
                result_filter=filter_with,
                sort_field=Result.name if sort_by is None else sort_by,
                sort_direction=Direction.ASC
                if sort_direction.capitalize() == "ASC"
                else Direction.DESC,
                page=curr_page,
                page_size=page_size,
            )

            results_list += results
            if page > 0 or len(results_list) >= total:
                break
            curr_page += 1

    if total > 0:
        return results


@results.command(name="get")
@click.argument("result-ids", type=str, nargs=-1, required=True)
@base_command(pass_config=True, auto_output="table")
def result_get(config: CliConfig, result_ids: List[str], **kwargs) -> Optional[List[Result]]:
    """Get details about multiple results given their RESULT_IDs."""
    with create_grpc_channel(config) as channel:
        results_client = ArmoniKResults(channel)
        results = []
        for result_id in result_ids:
            result = results_client.get_result(result_id)
            results.append(result)
        return results


@results.command(name="create")
@click.argument("session-id", type=str, required=True)
@click.option(
    "-r",
    "--result",
    "result_definitions",
    type=ResultNameDataParam(),
    required=True,
    multiple=True,
    help=(
        "Results to create. You can pass:\n"
        "1. --result <result_name> (only metadata is created).\n"
        "2. --result '<result_name> bytes <bytes>' (data is provided in bytes).\n"
        "3. --result '<result_name> file <filepath>' (data is provided from a file)."
    ),
)
@base_command(pass_config=True, auto_output="table")
def result_create(
    config: CliConfig,
    result_definitions: List[ResultNameDataParam.ParamType],
    session_id: str,
    **kwargs,
) -> Optional[List[Result]]:
    """Create result objects in a session with id SESSION_ID."""
    results_with_data = dict()
    metadata_only = []
    for res in result_definitions:
        if res.type == "bytes":
            results_with_data[res.name] = res.data
        elif res.type == "file":
            with open(res.data, "rb") as file:
                results_with_data[res.name] = file.read()
        elif res.type == "nodata":
            metadata_only.append(res.name)

    with create_grpc_channel(config) as channel:
        results_client = ArmoniKResults(channel)
        # Create metadata-only results
        created_results = []
        if len(metadata_only) > 0:
            created_results_metadata_only = results_client.create_results_metadata(
                result_names=metadata_only, session_id=session_id
            )
            created_results += created_results_metadata_only.values()
        # Create results with data
        if len(results_with_data.keys()) > 0:
            created_results_data = results_client.create_results(
                results_data=results_with_data, session_id=session_id
            )
            created_results += created_results_data.values()
        return created_results


@results.command(name="download-data")
@click.argument("session-id", type=str, required=True)
@click.option(
    "--id",
    "result_ids",
    type=str,
    multiple=True,
    required=True,
    help="Result IDs to download data from.",
)
@click.option(
    "--path",
    "download_path",
    type=click.Path(file_okay=False, dir_okay=True, writable=True, path_type=pathlib.Path),
    cls=MutuallyExclusiveOption,
    mutual=["std_out"],
    required=False,
    default=pathlib.Path.cwd(),
    help="Path to save the downloaded data in.",
)
@click.option(
    "--suffix",
    type=str,
    required=False,
    default="",
    help="Suffix to add to the downloaded files (File extension for example).",
)
@click.option(
    "--std-out",
    cls=MutuallyExclusiveOption,
    mutual=["path"],
    is_flag=True,
    help="When set, the downloaded data will be printed to the standard output.",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips results that haven't been found when trying to download them.",
)
@base_command(pass_config=True, auto_output="table")
def results_download_data(
    config: CliConfig,
    session_id: str,
    result_ids: List[str],
    download_path: pathlib.Path,
    suffix: str,
    std_out: Optional[bool],
    skip_not_found: bool,
    **kwargs,
):
    """Download a list of results from your cluster."""
    with create_grpc_channel(config) as channel:
        results_client = ArmoniKResults(channel)
        downloaded_results = []
        for result_id in result_ids:
            try:
                data = results_client.download_result_data(result_id, session_id)
            except grpc.RpcError as e:
                if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                    continue
                else:
                    raise e
            downloaded_result_obj = {"ResultId": result_id}
            if std_out:
                downloaded_result_obj["Data"] = data
                downloaded_result_table = [("ResultId", "ResultId"), ("Data", "Data")]
            else:
                result_download_path = download_path / (result_id + suffix)
                downloaded_result_table = [("ResultId", "ResultId"), ("Path", "Path")]
                with open(result_download_path, "wb") as result_file_handle:
                    result_file_handle.write(data)
                    downloaded_result_obj["Path"] = str(result_download_path)
            downloaded_results.append(downloaded_result_obj)
        console.formatted_print(
            downloaded_result_obj,
            print_format=config.output,
            table_cols=downloaded_result_table,
        )


@results.command(name="upload-data")
@click.argument("session-id", type=str, required=True)
@click.argument("result-id", type=str, required=True)
@click.option(
    "--from-bytes", type=str, cls=MutuallyExclusiveOption, mutual=["from_file"], require_one=True
)
@click.option(
    "--from-file",
    type=click.File("rb"),
    cls=MutuallyExclusiveOption,
    mutual=["from_bytes"],
    require_one=True,
)
@base_command(pass_config=True, auto_output="json")
def result_upload_data(
    config: CliConfig,
    session_id: str,
    result_id: Union[str, None],
    from_bytes: Union[str, None],
    from_file: IO[bytes],
    **kwargs,
) -> None:
    """Upload data for a result separately"""
    with create_grpc_channel(config) as channel:
        results_client = ArmoniKResults(channel)
        if from_bytes:
            result_data = bytes(from_bytes, encoding="utf-8")
        if from_file:
            result_data = from_file.read()

        results_client.upload_result_data(result_id, session_id, result_data)


@results.command(name="delete-data")
@click.argument("result-ids", type=str, nargs=-1, required=True)
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm the deletion of all result data without needing to do so for each result.",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips results that haven't been found when trying to delete them.",
)
@base_command(pass_config=True, auto_output="json")
def result_delete_data(
    config: CliConfig,
    logger: logging.Logger,
    result_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    **kwargs,
) -> None:
    """Delete the data of multiple results given their RESULT_IDs."""
    with create_grpc_channel(config) as channel:
        results_client = ArmoniKResults(channel)
        session_result_mapping = defaultdict(list)
        for result_id in result_ids:
            try:
                result = results_client.get_result(result_id)
            except grpc.RpcError as e:
                if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                    logger.warning("Couldn't find result with id=%s, skipping...", result_id)
                    continue
                else:
                    raise e
            if confirm or click.confirm(
                f"Are you sure you want to delete the result data of task [{result.owner_task_id}] in session [{result.session_id}]",
                abort=False,
            ):
                session_result_mapping[result.session_id].append(result_id)
        for session_id, result_ids_for_session in session_result_mapping.items():
            results_client.delete_result_data(result_ids_for_session, session_id)

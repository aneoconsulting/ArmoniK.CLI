import logging
import pathlib
import grpc
import armonik_cli_core as akcc

from typing import IO, List, Optional, Union
from collections import defaultdict

from armonik.client.results import ArmoniKResults
from armonik.common import Result, Direction
from armonik.common.filter import PartitionFilter, Filter


@akcc.group(name="result")
def results(**kwargs) -> None:
    """Manage results."""
    pass


@results.command(name="list", pass_config=True, auto_output="table")
@akcc.option(
    "-f",
    "--filter",
    "filter_with",
    type=akcc.FilterParam("Result"),
    required=False,
    help="An expression to filter the listed results with.",
    metavar="FILTER EXPR",
)
@akcc.option(
    "--sort-by",
    type=akcc.FieldParam("Result"),
    required=False,
    help="Attribute of result to sort with.",
)
@akcc.option(
    "--sort-direction",
    type=akcc.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    required=False,
    help="Whether to sort by ascending or by descending order.",
)
@akcc.option(
    "--page", default=-1, help="Get a specific page, it defaults to -1 which gets all pages."
)
@akcc.option("--page-size", default=100, help="Number of elements in each page")
def result_list(
    config: akcc.CliConfig,
    filter_with: Union[PartitionFilter, None],
    sort_by: Filter,
    sort_direction: str,
    page: int,
    page_size: int,
    **kwargs,
) -> None:
    """List the results of an ArmoniK cluster given <SESSION-ID>."""
    with akcc.create_grpc_channel(config) as channel:
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


@results.command(name="get", pass_config=True, auto_output="table")
@akcc.argument("result-ids", type=str, nargs=-1, required=True)
def result_get(config: akcc.CliConfig, result_ids: List[str], **kwargs) -> Optional[List[Result]]:
    """Get details about multiple results given their RESULT_IDs."""
    with akcc.create_grpc_channel(config) as channel:
        results_client = ArmoniKResults(channel)
        results = []
        for result_id in result_ids:
            result = results_client.get_result(result_id)
            results.append(result)
        return results


@results.command(name="create", pass_config=True, auto_output="table")
@akcc.argument("session-id", type=str, required=True)
@akcc.option(
    "-r",
    "--result",
    "result_definitions",
    type=akcc.ResultNameDataParam(),
    required=True,
    multiple=True,
    help=(
        "Results to create. You can pass:\n"
        "1. --result <result_name> (only metadata is created).\n"
        "2. --result '<result_name> bytes <bytes>' (data is provided in bytes).\n"
        "3. --result '<result_name> file <filepath>' (data is provided from a file)."
    ),
)
def result_create(
    config: akcc.CliConfig,
    result_definitions: List[akcc.ResultNameDataParam.ParamType],
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

    with akcc.create_grpc_channel(config) as channel:
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


@results.command(name="download-data", pass_config=True, auto_output="table")
@akcc.argument("session-id", type=str, required=True)
@akcc.option(
    "--id",
    "result_ids",
    type=str,
    multiple=True,
    required=True,
    help="Result IDs to download data from.",
)
@akcc.option(
    "--path",
    "download_path",
    type=akcc.Path(file_okay=False, dir_okay=True, writable=True, path_type=pathlib.Path),
    cls=akcc.MutuallyExclusiveOption,
    mutual=["std_out"],
    required=False,
    default=pathlib.Path.cwd(),
    help="Path to save the downloaded data in.",
)
@akcc.option(
    "--suffix",
    type=str,
    required=False,
    default="",
    help="Suffix to add to the downloaded files (File extension for example).",
)
@akcc.option(
    "--std-out",
    cls=akcc.MutuallyExclusiveOption,
    mutual=["path"],
    is_flag=True,
    help="When set, the downloaded data will be printed to the standard output.",
)
@akcc.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips results that haven't been found when trying to download them.",
)
def results_download_data(
    config: akcc.CliConfig,
    session_id: str,
    result_ids: List[str],
    download_path: pathlib.Path,
    suffix: str,
    std_out: Optional[bool],
    skip_not_found: bool,
    **kwargs,
):
    """Download a list of results from your cluster."""
    with akcc.create_grpc_channel(config) as channel:
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
        akcc.console.formatted_print(
            downloaded_result_obj,
            print_format=config.output,
            table_cols=downloaded_result_table,
        )


@results.command(name="upload-data", pass_config=True, auto_output="json")
@akcc.argument("session-id", type=str, required=True)
@akcc.argument("result-id", type=str, required=True)
@akcc.option(
    "--from-bytes",
    type=str,
    cls=akcc.MutuallyExclusiveOption,
    mutual=["from_file"],
    require_one=True,
)
@akcc.option(
    "--from-file",
    type=akcc.File("rb"),
    cls=akcc.MutuallyExclusiveOption,
    mutual=["from_bytes"],
    require_one=True,
)
def result_upload_data(
    config: akcc.CliConfig,
    session_id: str,
    result_id: Union[str, None],
    from_bytes: Union[str, None],
    from_file: IO[bytes],
    **kwargs,
) -> None:
    """Upload data for a result separately"""
    with akcc.create_grpc_channel(config) as channel:
        results_client = ArmoniKResults(channel)
        if from_bytes:
            result_data = bytes(from_bytes, encoding="utf-8")
        if from_file:
            result_data = from_file.read()

        results_client.upload_result_data(result_id, session_id, result_data)


@results.command(name="delete-data", pass_config=True, auto_output="json")
@akcc.argument("result-ids", type=str, nargs=-1, required=True)
@akcc.option(
    "--confirm",
    is_flag=True,
    help="Confirm the deletion of all result data without needing to do so for each result.",
)
@akcc.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips results that haven't been found when trying to delete them.",
)
def result_delete_data(
    config: akcc.CliConfig,
    logger: logging.Logger,
    result_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    **kwargs,
) -> None:
    """Delete the data of multiple results given their RESULT_IDs."""
    with akcc.create_grpc_channel(config) as channel:
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
            if confirm or akcc.confirm(
                f"Are you sure you want to delete the result data of task [{result.owner_task_id}] in session [{result.session_id}]",
                abort=False,
            ):
                session_result_mapping[result.session_id].append(result_id)
        for session_id, result_ids_for_session in session_result_mapping.items():
            results_client.delete_result_data(result_ids_for_session, session_id)

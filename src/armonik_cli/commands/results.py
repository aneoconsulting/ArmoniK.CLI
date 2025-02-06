from collections import defaultdict
import grpc
import rich_click as click

from typing import IO, List, Union

from armonik.client.results import ArmoniKResults
from armonik.common import Result, Direction
from armonik.common.filter import PartitionFilter, Filter

from armonik_cli.core import console, base_command, base_group
from armonik_cli.core.options import MutuallyExclusiveOption
from armonik_cli.core.params import FieldParam, FilterParam, ResultNameDataParam


RESULT_TABLE_COLS = [
    ("Name", "Name"),
    ("ID", "ResultId"),
    ("Status", "Status"),
    ("CreatedAt", "CreatedAt"),
]  # These should be configurable (through Config)


@click.group(name="result")
@base_group
def results() -> None:
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
@base_command
def result_list(
    endpoint: str,
    output: str,
    filter_with: Union[PartitionFilter, None],
    sort_by: Filter,
    sort_direction: str,
    page: int,
    page_size: int,
    debug: bool,
) -> None:
    """List the results of an ArmoniK cluster given <SESSION-ID>."""
    with grpc.insecure_channel(endpoint) as channel:
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
        console.formatted_print(results, print_format=output, table_cols=RESULT_TABLE_COLS)


@results.command(name="get")
@click.argument("result-ids", type=str, nargs=-1, required=True)
@base_command
def result_get(endpoint: str, output: str, result_ids: List[str], debug: bool) -> None:
    """Get details about multiple results given their RESULT_IDs."""
    with grpc.insecure_channel(endpoint) as channel:
        results_client = ArmoniKResults(channel)
        results = []
        for result_id in result_ids:
            result = results_client.get_result(result_id)
            results.append(result)
        console.formatted_print(results, print_format=output, table_cols=RESULT_TABLE_COLS)


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
@base_command
def result_create(
    endpoint: str,
    output: str,
    result_definitions: List[ResultNameDataParam.ParamType],
    session_id: str,
    debug: bool,
) -> None:
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

    with grpc.insecure_channel(endpoint) as channel:
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
        console.formatted_print(created_results, print_format=output, table_cols=RESULT_TABLE_COLS)


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
@base_command
def result_upload_data(
    endpoint: str,
    output: str,
    session_id: str,
    result_id: Union[str, None],
    from_bytes: Union[str, None],
    from_file: IO[bytes],
    debug: bool,
) -> None:
    """Upload data for a result separately"""
    with grpc.insecure_channel(endpoint) as channel:
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
@base_command
def result_delete_data(
    endpoint: str,
    output: str,
    result_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    debug: bool,
) -> None:
    """Delete the data of multiple results given their RESULT_IDs."""
    with grpc.insecure_channel(endpoint) as channel:
        results_client = ArmoniKResults(channel)
        session_result_mapping = defaultdict(list)
        for result_id in result_ids:
            try:
                result = results_client.get_result(result_id)
            except grpc.RpcError as e:
                if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                    console.print(f"Couldn't find result with id={result_id}, skipping...")
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

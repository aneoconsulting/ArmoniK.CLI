from collections import defaultdict
import grpc
import rich_click as click

from typing import IO, List, Optional, Union

from armonik.client import ArmoniKResults
from armonik.common import (
    Result,
    Direction,
    EventTypes,
    NewResultEvent,
    ResultStatusUpdateEvent,
    ResultStatus,
)
from armonik.common.filter import ResultFilter, Filter

from armonik_cli.commands.watch import (
    Watch,
    WatchDisplay,
    WatchGroup,
    WatchGroupDisplay,
    create_nonblocking_event_handler,
)
from armonik_cli.core import console, base_command, base_group
from armonik_cli.core.common import calculate_duration, format_timestamp
from armonik_cli.core.options import MutuallyExclusiveOption
from armonik_cli.core.params import FieldParam, FilterParam, ResultNameDataParam

from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.layout import Layout

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
    filter_with: Union[ResultFilter, None],
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


class ResultWatch(Watch[Result, ResultStatus]):
    """Watches and tracks the status of a single ArmoniK `Result`.

    This class wraps around a `Result` object, observing status changes and
    maintaining a status history (via its `status_tracker`).
    """

    status_cls = ResultStatus

    def refresh(self, client: ArmoniKResults):
        """Refresh the data of this result via a gRPC call.

        Uses the provided client to retrieve the latest `Result` object and
        updates the internal data and current status accordingly.

        Args:
            client (ArmoniKResults): An ArmoniKResults client.
        """
        self.data = client.get_result(self.id)
        self._current_status = ResultStatus(self.data.status).name


class ResultsWatchGroup(WatchGroup[ResultFilter]):
    """Watches and monitors multiple ArmoniK results, displaying live updates.

    This group manages multiple `ResultWatch` instances and registers event handlers
    for real-time monitoring of result statuses.
    """

    def _init_populate_watches(self):
        """Populate the watch dictionary with `ResultWatch` objects.

        1. Initializes the `results_client` using the gRPC channel.
        2. If `entity_ids` are provided:
            - Creates a `ResultWatch` for each specified ID and refreshes it immediately.
        3. Otherwise, lists results from the server using the given filter or session ID:
            - If no results are returned and the session ID is still unknown, prompt the user to enter one.
            - For each returned result, creates a corresponding `ResultWatch` and sets its data.

        Raises:
            Prompt: If no results are found and no session ID is available,
                prompts the user to supply a session ID in the terminal.
        """
        self.results_client = ArmoniKResults(self.grpc_channel)
        if self.entity_ids:
            for result_id in self.entity_ids:
                self.watches[result_id] = ResultWatch(result_id)
                self.watches[result_id].refresh(self.results_client)
        else:
            watchable_results_count, watchable_results = self.results_client.list_results(
                result_filter=self.filter_with,
                page=0,
                page_size=self.limit,
                sort_field=Result.created_at if self.sort_by is None else self.sort_by,
                sort_direction=Direction.ASC
                if self.sort_direction.capitalize() == "ASC"
                else Direction.DESC,
            )
            # (most likely) No session id was provided in the filter nor passed along, so we ask for it again
            if watchable_results_count == 0 and not self.session_id:
                self.session_id = click.prompt(
                    "No results available to watch, you can however specify a session and results that satisfy said filter within session will be watched automatically"
                )
            for result in watchable_results:
                self.watches[result.result_id] = ResultWatch(result.result_id)
                self.watches[result.result_id].data = result

    def _register_event_handlers(self):
        """Register event handlers for result status updates and new results.

        Spawns one or more background threads via `create_nonblocking_event_handler` to:
          - Listen for `RESULT_STATUS_UPDATE` events and call `update_watch_status`.
          - If a filter is provided, also listen for `NEW_RESULT` events to automatically
            add newly created results to the watch group.
        """
        self.status_update_handler = create_nonblocking_event_handler(
            self.grpc_channel,
            self.session_id,
            [EventTypes.RESULT_STATUS_UPDATE],
            [self.update_watch_status],
        )
        self.status_update_handler.start()
        if (
            self.filter_with is not None
        ):  # NOTE: This doesn't work well for results since they're all created at the start, instead maybe look into some sort of scheduled polling until we fill?
            self.autofill_handler = create_nonblocking_event_handler(
                self.grpc_channel,
                self.session_id,
                [EventTypes.NEW_RESULT],
                [self.autofill],
                result_filter=self.filter_with,
            )
            self.autofill_handler.start()

    def update_watch_status(
        self, session_id: str, event_type: EventTypes, event: ResultStatusUpdateEvent
    ) -> bool:
        """Update the status of a result upon receiving a `RESULT_STATUS_UPDATE` event.

        If the reported `result_id` is already being watched, its current status
        is updated to match the new status from the event.

        Args:
            session_id (str): The session ID for which the event applies.
            event_type (EventTypes): The type of the event (must be `RESULT_STATUS_UPDATE`).
            event (ResultStatusUpdateEvent): The event data containing the updated status.

        Returns:
            bool: Always returns False, allowing the event listener to keep running.
        """
        if event_type == EventTypes.RESULT_STATUS_UPDATE and event.result_id in self.watches:
            self.watches[event.result_id].current_status = ResultStatus(event.status).name
        return False

    def autofill(self, session_id: str, event_type: EventTypes, event: NewResultEvent) -> bool:
        """Callback for handling new results events to fill up the watches if we're under the limit.

        Args:
            session_id (str): The session ID associated with the event.
            event_type (EventTypes): The type of the event.
            event (NewResultEvent): The event data containing the new result information.

        Returns:
            bool: Always returns False to not close the session.
        """
        if len(list(self.watches.keys())) < self.limit and event_type == EventTypes.NEW_RESULT:
            self.watches[event.result_id] = ResultWatch(event.result_id)
            self.watches[event.result_id].refresh(self.results_client)
        return False


class ResultWatchDisplay(WatchDisplay):
    def _create_metadata_display(self):
        """Create a display panel for the results metadata.

        Returns:
            Panel: A Rich Panel containing results metadata.
        """
        metadata_table = Table(title="Results metadata", show_header=False, border_style="yellow")

        metadata_table.add_column("Label", style="cyan")
        metadata_table.add_column("Value")

        if self.watch.data:
            metadata_table.add_row(
                "[bold]Name[/bold]",
                self.watch.data.name,
            )
            metadata_table.add_row(
                "[bold]Session ID[/bold]",
                f"[link=http://{self.endpoint}/admin/en/tasks?0-root-1-0={self.watch.data.session_id}]{self.watch.data.session_id}[/link]"
                if self.endpoint
                else self.watch.data.session_id,
            )
            metadata_table.add_row(
                "Owner Task ID",
                f"[link=http://{self.endpoint}/admin/en/tasks?0-root-1-0={self.watch.data.owner_task_id}]{self.watch.data.session_id}[/link]"
                if self.endpoint
                else self.watch.data.owner_task_id,
            )
            metadata_table.add_row("Created By", self.watch.data.created_by)
            metadata_table.add_row(
                "Size",
                str(self.watch.data.size),
            )
        else:
            metadata_table.add_row("Data not yet retrieved")

        metadata_panel = Panel(metadata_table)
        return metadata_panel

    def _create_status_display(self):
        """Create a display panel for the results status.

        Returns:
            Panel: A Rich Panel containing results status.
        """
        table = Table(
            title=f"[bold]Result ID:[/bold] [link=http://{self.endpoint}/admin/en/results/{self.watch.id}]{self.watch.id}[/link]"
            if self.endpoint
            else self.watch.id,
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
        )

        table.add_column("Status", style="cyan")
        table.add_column("Start Time", style="green")
        table.add_column("Duration", style="yellow")

        table_rows = []
        for status, entries in self.watch.status_tracker.items():
            if entries:  # Only show statuses that have occurred
                for entry in entries:
                    table_rows.append(
                        (
                            status,
                            format_timestamp(entry["start"]),
                            str(calculate_duration(entry["start"], entry["end"])),
                        )
                    )

        for status, start, dur in sorted(table_rows, key=lambda v: v[1]):
            table.add_row(status, start, dur)
        table.expand = True
        return Panel(table, title="Live Status Tracking", border_style="green")


class ResultsWatchGroupDisplay(WatchGroupDisplay):
    """Class for displaying information about monitored results"""

    def display(self):
        """Assemble the full layout for the live display.

        Returns:
            Layout: A Rich Layout object combining the navigation bar, status history,
            and task metadata panels.
        """
        nav_bar = Layout(self.create_navigation_bar(), name="nav")
        nav_bar.size = 2
        help_bar = Layout(self.create_help_bar(), name="help")
        help_bar.size = 1
        full_layout = Layout()
        if self.watches:
            watch_display = ResultWatchDisplay(
                self.watches[self.current_tab], self.endpoint
            ).display()
        else:
            watch_display = Panel(Text("Nothing to watch.."))
        full_layout.split_column(nav_bar, Layout(watch_display, name="content"), help_bar)
        return full_layout


@results.command("watch")
@click.option(
    "--id",
    "result_ids",
    cls=MutuallyExclusiveOption,
    mutual=["filter_with"],
    require_one=True,
    type=str,
    default=[],
    multiple=True,
    metavar="RESULT_IDS",
)
@click.option(
    "-f",
    "--filter",
    "filter_with",
    type=FilterParam("Result"),
    cls=MutuallyExclusiveOption,
    mutual=["result_ids"],
    require_one=True,
    required=False,
    help="An expression to filter for results to watch with.",
    metavar="FILTER EXPR",
)
@click.option(
    "--limit",
    cls=MutuallyExclusiveOption,
    mutual=["result_ids"],
    type=int,
    required=False,
    default=1,
    help="The maximum number of results to retrieve when using a filter.",
)
@click.option(
    "--session-id",
    type=str,
    required=False,
    help="Id of the session to look for the result in if none were specified in the filter",
    metavar="SESSION_ID",
)
@click.option(
    "--sort-by",
    type=FieldParam("Result"),
    required=False,
    help="Attribute of results to sort with.",
)
@click.option(
    "--sort-direction",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    required=False,
    help="Whether to sort by ascending or by descending order.",
)
@base_command
def results_watch(
    endpoint: str,
    output: str,
    filter_with: Optional[ResultFilter],
    result_ids: List[str],
    limit: int,
    session_id: Optional[str],
    sort_by,
    sort_direction,
    debug: bool,
) -> None:
    """Start a watch session to get a live overview of results in your cluster."""
    # The ResultsWatchGroup creates watches for us and spawns threads to update the different watches
    result_watchers = ResultsWatchGroup(
        endpoint=endpoint,
        debug=debug,
        filter_with=filter_with,
        session_id=session_id,
        limit=limit,
        entity_ids=result_ids,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    result_display = ResultsWatchGroupDisplay(result_watchers.get_watches_view(), endpoint)
    # open file and dump print(f"Channel state <{time.time()}>: {self.grpc_channel.get_state()}") onto it
    with Live(result_display.display(), refresh_per_second=10, screen=True) as live:
        while True:
            result_display.update()
            result_display.update_contents(result_watchers.get_watches_view())
            live.update(result_display.display())
    pass

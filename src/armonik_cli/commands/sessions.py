from time import sleep
import grpc
import rich_click as click

from datetime import timedelta
from typing import Dict, List, Tuple, Union

from armonik.client.sessions import ArmoniKSessions
from armonik.common import Session, TaskOptions, Direction
from armonik.common.filter import SessionFilter, Filter

from armonik_cli.core import (
    console,
    base_command,
    KeyValuePairParam,
    TimeDeltaParam,
    FilterParam,
    base_group,
)
from armonik_cli.core.params import FieldParam

from rich.panel import Panel

SESSION_TABLE_COLS = [("ID", "SessionId"), ("Status", "Status"), ("CreatedAt", "CreatedAt")]


@click.group(name="session")
@base_group
def sessions() -> None:
    """Manage cluster sessions."""
    pass


@sessions.command(name="list")
@click.option(
    "-f",
    "--filter",
    "filter_with",
    type=FilterParam("Session"),
    required=False,
    help="An expression to filter the sessions to be listed.",
    metavar="FILTER EXPR",
)
@click.option(
    "--sort-by",
    type=FieldParam("Session"),
    required=False,
    help="Attribute of session to sort with.",
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
def session_list(
    endpoint: str,
    output: str,
    filter_with: Union[SessionFilter, None],
    sort_by: Filter,
    sort_direction: str,
    page: int,
    page_size: int,
    debug: bool,
) -> None:
    """List the sessions of an ArmoniK cluster."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        curr_page = page if page > 0 else 0
        session_list = []
        while True:
            total, sessions = sessions_client.list_sessions(
                session_filter=filter_with,
                sort_field=Session.session_id if sort_by is None else sort_by,
                sort_direction=Direction.ASC
                if sort_direction.capitalize() == "ASC"
                else Direction.DESC,
                page=curr_page,
                page_size=page_size,
            )
            session_list += sessions
            if page > 0 or len(session_list) >= total:
                break
            curr_page += 1

    if total > 0:
        console.formatted_print(session_list, print_format=output, table_cols=SESSION_TABLE_COLS)

    # TODO: Use logger to display this information
    # console.print(f"\n{total} sessions found.")


@sessions.command(name="get")
@click.argument("session-ids", required=True, type=str, nargs=-1)
@base_command
def session_get(endpoint: str, output: str, session_ids: List[str], debug: bool) -> None:
    """Get details of a given session."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        sessions = []
        for session_id in session_ids:
            session = sessions_client.get_session(session_id=session_id)
            sessions.append(session)
        console.formatted_print(sessions, print_format=output, table_cols=SESSION_TABLE_COLS)


@sessions.command(name="create")
@click.option(
    "--max-retries",
    type=int,
    required=True,
    help="Maximum default number of execution attempts for session tasks.",
    metavar="NUM_RETRIES",
)
@click.option(
    "--max-duration",
    type=TimeDeltaParam(),
    required=True,
    help="Maximum default task execution time (format HH:MM:SS.MS).",
    metavar="DURATION",
)
@click.option(
    "--priority", type=int, required=True, help="Default task priority.", metavar="PRIORITY"
)
@click.option(
    "--partition",
    type=str,
    multiple=True,
    help="Partition to add to the session.",
    metavar="PARTITION",
)
@click.option(
    "--default-partition",
    type=str,
    default="default",
    show_default=True,
    help="Default partition.",
    metavar="PARTITION",
)
@click.option(
    "--application-name", type=str, required=False, help="Default application name.", metavar="NAME"
)
@click.option(
    "--application-version",
    type=str,
    required=False,
    help="Default application version.",
    metavar="VERSION",
)
@click.option(
    "--application-namespace",
    type=str,
    required=False,
    help="Default application namespace.",
    metavar="NAMESPACE",
)
@click.option(
    "--application-service",
    type=str,
    required=False,
    help="Default application service.",
    metavar="SERVICE",
)
@click.option(
    "--engine-type", type=str, required=False, help="Default engine type.", metavar="ENGINE_TYPE"
)
@click.option(
    "--option",
    type=KeyValuePairParam(),
    required=False,
    multiple=True,
    help="Additional default options.",
    metavar="KEY=VALUE",
)
@base_command
def session_create(
    endpoint: str,
    max_retries: int,
    max_duration: timedelta,
    priority: int,
    partition: Union[List[str], None],
    default_partition: str,
    application_name: Union[str, None],
    application_version: Union[str, None],
    application_namespace: Union[str, None],
    application_service: Union[str, None],
    engine_type: Union[str, None],
    option: Union[List[Tuple[str, str]], None],
    output: str,
    debug: bool,
) -> None:
    """Create a new session."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        session_id = sessions_client.create_session(
            default_task_options=TaskOptions(
                max_duration=max_duration,
                priority=priority,
                max_retries=max_retries,
                partition_id=default_partition,
                application_name=application_name,
                application_version=application_version,
                application_namespace=application_namespace,
                application_service=application_service,
                engine_type=engine_type,
                options=dict(option) if option else None,
            ),
            partition_ids=partition if partition else [default_partition],
        )
        session = sessions_client.get_session(session_id=session_id)
        console.formatted_print(session, print_format=output, table_cols=SESSION_TABLE_COLS)


@sessions.command(name="cancel")
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm the cancel operation on all supplied sessions all at once in advance.",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to cancel them.",
)
@click.argument("session-ids", required=True, type=str, nargs=-1)
@base_command
def session_cancel(
    endpoint: str,
    output: str,
    session_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    debug: bool,
) -> None:
    """Cancel sessions."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        cancelled_sessions = []
        for session_id in session_ids:
            if confirm or click.confirm(
                f"Are you sure you want to cancel the session with id [{session_id}]",
                abort=False,
            ):
                try:
                    session = sessions_client.cancel_session(session_id=session_id)
                    cancelled_sessions.append(session)
                except grpc.RpcError as e:
                    if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                        console.print(f"Couldn't find session with id={session_id}, skipping...")
                        continue
                    else:
                        raise e
        console.formatted_print(
            cancelled_sessions, print_format=output, table_cols=SESSION_TABLE_COLS
        )


@sessions.command(name="pause")
@click.argument("session-ids", required=True, type=str, nargs=-1)
@base_command
def session_pause(endpoint: str, output: str, session_ids: List[str], debug: bool) -> None:
    """Pause sessions."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        paused_sessions = []
        for session_id in session_ids:
            session = sessions_client.pause_session(session_id=session_id)
            paused_sessions.append(session)
        console.formatted_print(paused_sessions, print_format=output, table_cols=SESSION_TABLE_COLS)


@sessions.command(name="resume")
@click.argument("session-ids", required=True, type=str, nargs=-1)
@base_command
def session_resume(endpoint: str, output: str, session_ids: List[str], debug: bool) -> None:
    """Resume sessions."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        resumed_sessions = []
        for session_id in session_ids:
            session = sessions_client.resume_session(session_id=session_id)
            resumed_sessions.append(session)
        console.formatted_print(
            resumed_sessions, print_format=output, table_cols=SESSION_TABLE_COLS
        )


@sessions.command(name="close")
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm the close operation on all supplied sessions all at once in advance.",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to close them.",
)
@click.argument("session-ids", required=True, type=str, nargs=-1)
@base_command
def session_close(
    endpoint: str,
    output: str,
    session_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    debug: bool,
) -> None:
    """Close sessions."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        closed_sessions = []
        for session_id in session_ids:
            if confirm or click.confirm(
                f"Are you sure you want to close the session with id [{session_id}]",
                abort=False,
            ):
                try:
                    session = sessions_client.close_session(session_id=session_id)
                    closed_sessions.append(session)
                except grpc.RpcError as e:
                    if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                        console.print(f"Couldn't find session with id={session_id}, skipping...")
                        continue
                    else:
                        raise e
        console.formatted_print(closed_sessions, print_format=output, table_cols=SESSION_TABLE_COLS)


@sessions.command(name="purge")
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm the purge operation on all supplied sessions all at once in advance.",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to purge them.",
)
@click.argument("session-ids", required=True, type=str, nargs=-1)
@base_command
def session_purge(
    endpoint: str,
    output: str,
    session_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    debug: bool,
) -> None:
    """Purge sessions."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        purged_sessions = []
        for session_id in session_ids:
            if confirm or click.confirm(
                f"Are you sure you want to purge the session with id [{session_id}]",
                abort=False,
            ):
                try:
                    session = sessions_client.purge_session(session_id=session_id)
                    purged_sessions.append(session)
                except grpc.RpcError as e:
                    if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                        console.print(f"Couldn't find session with id={session_id}, skipping...")
                        continue
                    else:
                        raise e

        console.formatted_print(purged_sessions, print_format=output, table_cols=SESSION_TABLE_COLS)


@sessions.command(name="delete")
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm the delete operation on all supplied sessions all at once in advance.",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to delete them.",
)
@click.argument("session-ids", required=True, type=str, nargs=-1)
@base_command
def session_delete(
    endpoint: str,
    output: str,
    session_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    debug: bool,
) -> None:
    """Delete sessions and their associated tasks from the cluster."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        deleted_sessions = []
        for session_id in session_ids:
            if confirm or click.confirm(
                f"Are you sure you want to delete the session with id [{session_id}]",
                abort=False,
            ):
                try:
                    session = sessions_client.delete_session(session_id=session_id)
                    deleted_sessions.append(session)
                except grpc.RpcError as e:
                    if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                        console.print(f"Couldn't find session with id={session_id}, skipping...")
                        continue
                    else:
                        raise e
        console.formatted_print(
            deleted_sessions, print_format=output, table_cols=SESSION_TABLE_COLS
        )


@sessions.command(name="stop-submission")
@click.option(
    "--clients",
    is_flag=True,
    default=False,
    help="Prevent clients from submitting new tasks in the session.",
)
@click.option(
    "--workers",
    is_flag=True,
    default=False,
    help="Prevent workers from submitting new tasks in the session.",
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm the block submission operation on all supplied sessions all at once in advance.",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to block submission to them.",
)
@click.argument("session-ids", required=True, type=str, nargs=-1)
@base_command
def session_stop_submission(
    endpoint: str,
    session_ids: str,
    confirm: bool,
    clients: bool,
    workers: bool,
    skip_not_found: bool,
    output: str,
    debug: bool,
) -> None:
    """Stop clients and/or workers from submitting new tasks in a session."""
    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        submission_blocked_sessions = []
        for session_id in session_ids:
            blocked_submitters = (
                ("clients" if clients else "")
                + (" and " if clients and workers else "")
                + ("workers" if workers else "")
            )
            if confirm or click.confirm(
                f"Are you sure you want to stop {blocked_submitters} from submitting tasks to the session with id [{session_id}]",
                abort=False,
            ):
                try:
                    session = sessions_client.stop_submission_session(
                        session_id=session_id, client=clients, worker=workers
                    )
                    submission_blocked_sessions.append(session)
                except grpc.RpcError as e:
                    if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                        console.print(f"Couldn't find session with id={session_id}, skipping...")
                        continue
                    else:
                        raise e
        console.formatted_print(
            submission_blocked_sessions,
            print_format=output,
            table_cols=SESSION_TABLE_COLS,
        )



# from armonik.client import ArmoniKTasks
# from armonik.common import Task, SessionStatus, TaskStatus
# from rich.live import Live
# from rich.layout import Layout
# from rich.table import Table
# from rich.text import Text
# import time

# def create_session_watch_display(session_info: Session, status_count: Dict[TaskStatus, int]):
#     # Display a table with meta data about the task and then set up a layout where you show the number of items in each status, along with the percentage of the total, sort of like a mini dashboard
#     layout = Layout(name="root")
#     layout.split(Layout(name="header"), Layout(name="body"))

#     # Create header panel with session info
#     header_text = Text(f"Session ID: {session_info.session_id}\n")
#     header_text.append(f"Created At: {session_info.created_at}\n")
#     header_text.append(f"Status: {SessionStatus(session_info.status).name}\n")
#     header_panel = Panel(header_text, title="Session Info")

#     # Create body panel with task status counts
#     total_tasks = sum(status_count.values())
#     body_table = Table(title="Task Status Counts")
#     body_table.add_column("Status", justify="right", style="cyan", no_wrap=True)
#     body_table.add_column("Count", justify="right", style="magenta")
#     body_table.add_column("Percentage", justify="right", style="green")

#     for status, count in status_count.items():
#         percentage = (count / total_tasks) * 100 if total_tasks > 0 else 0
#         body_table.add_row(status.name, str(count), f"{percentage:.2f}%")

#     body_panel = Panel(body_table)

#     layout["header"].update(header_panel)
#     layout["body"].update(body_panel)

#     return layout

from armonik.client import ArmoniKTasks, ArmoniKSessions
from armonik.common import Task, SessionStatus, TaskStatus
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.bar import Bar
from typing import Dict
import time
import click
import grpc
from rich.live import Live
from time import sleep

STATUS_COLORS = {
    TaskStatus.CREATING: "grey37",
    TaskStatus.PROCESSING: "yellow",
    TaskStatus.COMPLETED: "green",
    TaskStatus.CANCELLED: "red",
    TaskStatus.ERROR: "bold red",
    TaskStatus.UNSPECIFIED: "bright_black",
}


FLASH_STYLE = "strike "  # “flash” color/style

def create_session_watch_display(
    session_info, 
    status_count: Dict[TaskStatus, int],
    last_change_time: Dict[TaskStatus, float],
    flash_duration: float
):
    """Create a layout that flashes panels when counts change."""
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=5),
        Layout(name="statuses", ratio=1),
    )

    header_table = Table(show_header=False)
    header_table.add_column("Label", style="bold cyan")
    header_table.add_column("Value", style="cyan")
    header_table.add_row("[bold]Session ID:[/bold]", session_info.session_id, style="cyan")
    header_table.add_row("[bold]Created at:[/bold]", str(session_info.created_at), style="cyan")
    header_table.add_row(
        "[bold]Status:[/bold]",
        Text(
            SessionStatus(session_info.status).name,
            style="green" if session_info.status == SessionStatus.RUNNING else "yellow"
        )
    )

    total_tasks = sum(status_count.values())

    statuses_table = Table.grid(expand=True)
    columns_per_row = 5
    row_items = []
    now = time.time()  

    # Iterate over *all* TaskStatus values to keep layout fixed
    for status in TaskStatus:
        count = status_count.get(status, 0)
        percentage = (count / total_tasks) * 100 if total_tasks > 0 else 0

        # Decide if we "flash" this panel
        time_since_change = now - last_change_time.get(status, 0)
        if time_since_change < flash_duration:
            # recently changed -> special "flash" style
            border_style = FLASH_STYLE + STATUS_COLORS.get(status, "white")
        else:
            # normal color for that status
            border_style = STATUS_COLORS.get(status, "white")

        panel_text = Text()
        panel_text.append(f"{status.name}\n", style="bold")
        panel_text.append(f"Count: {count}\n", style="white")
        panel_text.append(f"{percentage:.2f}%", style="white")

        panel = Panel(
            panel_text,
            border_style=border_style,
        )

        row_items.append(panel)

        if len(row_items) == columns_per_row:
            statuses_table.add_row(*row_items)
            row_items = []

    if row_items:
        statuses_table.add_row(*row_items)

    layout["statuses"].update(statuses_table)

    completed_tasks = status_count.get(TaskStatus.COMPLETED, 0)

    layout["header"].split_row(
        header_table, 
        Panel(Text.from_markup(f"[bold]Completed:[/bold] {completed_tasks}/{total_tasks}", justify="center"))
    )
    return layout

@sessions.command("watch")
@click.argument("session-id", required=True, type=str)
@click.option("--refresh-rate", type=int, default=10, help="Refresh rate in seconds.")
@base_command
def sessions_watch(
    endpoint: str,
    session_id: str,
    refresh_rate: int,
    output: str,
    debug: bool,
):
    previous_counts = {}
    last_change_time = {}
    flash_duration = 0.5  # half-second flash

    with grpc.insecure_channel(endpoint) as channel:
        sessions_client = ArmoniKSessions(channel)
        tasks_client = ArmoniKTasks(channel)

        # Fetch initial data
        session_info = sessions_client.get_session(session_id)
        status_count = tasks_client.count_tasks_by_status(Task.session_id == session_id)
        previous_counts = status_count.copy()

        # Render the initial layout
        display = create_session_watch_display(
            session_info, status_count, last_change_time, flash_duration
        )

        with Live(display, refresh_per_second=refresh_rate, screen=True) as live:
            while True:
                start_loop = time.time()

                # Get updated data
                session_info = sessions_client.get_session(session_id)
                status_count = tasks_client.count_tasks_by_status(
                    Task.session_id == session_id
                )

                # Check for changes and record the time
                for st, new_value in status_count.items():
                    old_value = previous_counts.get(st, 0)
                    if new_value != old_value:
                        last_change_time[st] = time.time()

                # Also handle statuses that might have been in previous_counts
                # but no longer appear in status_count
                for st in previous_counts:
                    if st not in status_count:
                        if previous_counts[st] != 0:
                            last_change_time[st] = time.time()

                # Update the Live display
                display = create_session_watch_display(
                    session_info, status_count, last_change_time, flash_duration
                )
                live.update(display)

                # Update previous counts to the current ones
                previous_counts = status_count.copy()

                # Sleep to maintain refresh rate
                elapsed = time.time() - start_loop
                to_sleep = (1 / refresh_rate) - elapsed
                if to_sleep > 0:
                    time.sleep(to_sleep)
import grpc
import rich_click as click

from datetime import timedelta
from typing import List, Tuple, Union, Optional

from armonik.client import ArmoniKTasks
from armonik.common import Task, TaskStatus, TaskDefinition, TaskOptions, Direction, Filter
from armonik.common.filter import TaskFilter

from armonik_cli.commands.watch import (
    Watch,
    WatchDisplay,
    WatchGroup,
    WatchGroupDisplay,
    create_nonblocking_event_handler,
)
from armonik_cli.core.common import format_timestamp, calculate_duration
from armonik_cli.core import console, base_command, base_group
from armonik_cli.core.options import MutuallyExclusiveOption
from armonik_cli.core.params import KeyValuePairParam, TimeDeltaParam, FilterParam, FieldParam
from armonik.client.events import (
    EventTypes,
    TaskStatusUpdateEvent,
    NewTaskEvent,
)

from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.layout import Layout

TASKS_TABLE_COLS = [("ID", "Id"), ("Status", "Status"), ("CreatedAt", "CreatedAt")]


@click.group(name="task")
@base_group
def tasks() -> None:
    """Manage cluster's tasks."""
    pass


@tasks.command(name="list")
@click.option(
    "-f",
    "--filter",
    "filter_with",
    type=FilterParam("Task"),
    required=False,
    help="An expression to filter the listed tasks with.",
    metavar="FILTER EXPR",
)
@click.option(
    "--sort-by", type=FieldParam("Task"), required=False, help="Attribute of task to sort with."
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
def tasks_list(
    endpoint: str,
    output: str,
    filter_with: Union[TaskFilter, None],
    sort_by: Filter,
    sort_direction: str,
    page: int,
    page_size: int,
    debug: bool,
) -> None:
    "List all tasks."
    with grpc.insecure_channel(endpoint) as channel:
        tasks_client = ArmoniKTasks(channel)
        curr_page = page if page > 0 else 0
        tasks_list = []
        while True:
            total, curr_tasks_list = tasks_client.list_tasks(
                task_filter=filter_with,
                sort_field=Task.id if sort_by is None else sort_by,
                sort_direction=Direction.ASC
                if sort_direction.capitalize() == "ASC"
                else Direction.DESC,
                page=curr_page,
                page_size=page_size,
            )
            tasks_list += curr_tasks_list

            if page > 0 or len(tasks_list) >= total:
                break
            curr_page += 1

    if total > 0:
        console.formatted_print(tasks_list, print_format=output, table_cols=TASKS_TABLE_COLS)


@tasks.command(name="get")
@click.argument("task-ids", type=str, nargs=-1, required=True)
@base_command
def tasks_get(endpoint: str, output: str, task_ids: List[str], debug: bool):
    """Get a detailed overview of set of tasks given their ids."""
    with grpc.insecure_channel(endpoint) as channel:
        tasks_client = ArmoniKTasks(channel)
        tasks = []
        for task_id in task_ids:
            task = tasks_client.get_task(task_id)
            tasks.append(task)
        console.formatted_print(tasks, print_format=output, table_cols=TASKS_TABLE_COLS)


@tasks.command(name="cancel")
@click.argument("task-ids", type=str, nargs=-1, required=True)
@base_command
def tasks_cancel(endpoint: str, output: str, task_ids: List[str], debug: bool):
    "Cancel tasks given their ids. (They don't have to be in the same session necessarily)."
    with grpc.insecure_channel(endpoint) as channel:
        tasks_client = ArmoniKTasks(channel)
        tasks_client.cancel_tasks(task_ids)


@tasks.command(name="create")
@click.option(
    "--session-id",
    type=str,
    required=True,
    help="Id of the session to create the task in.",
    metavar="SESSION_ID",
)
@click.option(
    "--payload-id",
    type=str,
    required=True,
    help="Id of the payload to associated to the task.",
    metavar="PAYLOAD_ID",
)
@click.option(
    "--expected-outputs",
    multiple=True,
    required=True,
    help="List of the ids of the task's outputs.",
    metavar="EXPECTED_OUTPUTS",
)
@click.option(
    "--data-dependencies",
    multiple=True,
    help="List of the ids of the task's data dependencies.",
    metavar="DATA_DEPENDENCIES",
)
@click.option(
    "--max-retries",
    type=int,
    default=None,
    help="Maximum default number of execution attempts for this task.",
    metavar="NUM_RETRIES",
)
@click.option(
    "--max-duration",
    type=TimeDeltaParam(),
    default=None,
    help="Maximum default task execution time (format HH:MM:SS.MS).",
    metavar="DURATION",
)
@click.option("--priority", default=None, type=int, help="Task priority.", metavar="PRIORITY")
@click.option(
    "--partition-id",
    type=str,
    help="Partition to run the task in.",
    metavar="PARTITION",
)
@click.option(
    "--application-name",
    type=str,
    required=False,
    help="Application name for this task.",
    metavar="NAME",
)
@click.option(
    "--application-version",
    type=str,
    required=False,
    help="Application version for this task.",
    metavar="VERSION",
)
@click.option(
    "--application-namespace",
    type=str,
    required=False,
    help="Application namespace for this task.",
    metavar="NAMESPACE",
)
@click.option(
    "--application-service",
    type=str,
    required=False,
    help="Application service for this task.",
    metavar="SERVICE",
)
@click.option("--engine-type", type=str, required=False, help="Engine type.", metavar="ENGINE_TYPE")
@click.option(
    "--options",
    type=KeyValuePairParam(),
    default=None,
    multiple=True,
    help="Additional task options.",
    metavar="KEY=VALUE",
)
@base_command
def tasks_create(
    endpoint: str,
    output: str,
    session_id: str,
    payload_id: str,
    expected_outputs: List[str],
    data_dependencies: Union[List[str], None],
    max_retries: Union[int, None],
    max_duration: Union[timedelta, None],
    priority: Union[int, None],
    partition_id: Union[str, None],
    application_name: Union[str, None],
    application_version: Union[str, None],
    application_namespace: Union[str, None],
    application_service: Union[str, None],
    engine_type: Union[str, None],
    options: Union[List[Tuple[str, str]], None],
    debug: bool,
):
    """Create a task."""
    with grpc.insecure_channel(endpoint) as channel:
        tasks_client = ArmoniKTasks(channel)
        task_options = None
        if max_duration is not None and priority is not None and max_retries is not None:
            task_options = TaskOptions(
                max_duration,
                priority,
                max_retries,
                partition_id,
                application_name,
                application_version,
                application_namespace,
                application_service,
                engine_type,
                options,
            )
        elif any(arg is not None for arg in [max_duration, priority, max_retries]):
            console.print(
                click.style(
                    "If you want to pass in additional task options please provide all three (max duration, priority, max retries)",
                    "red",
                )
            )
            raise click.MissingParameter(
                "If you want to pass in additional task options please provide all three (max duration, priority, max retries)"
            )
        task_definition = TaskDefinition(
            payload_id, expected_outputs, data_dependencies, task_options
        )
        submitted_tasks = tasks_client.submit_tasks(session_id, [task_definition])

        console.formatted_print(
            submitted_tasks[0],
            print_format=output,
            table_cols=TASKS_TABLE_COLS,
        )


class TaskWatch(Watch[Task, TaskStatus]):
    """Class that tracks the status and data of a Task"""

    status_cls = TaskStatus

    def refresh(self, client):
        """Refreshes the data of the watched task via a gRPC call."""
        self.data.refresh(client)
        self.current_status = TaskStatus(
            self.data.status
        ).name  # If things go haywire it's probably this


class TasksWatchGroup(WatchGroup[TaskFilter]):
    """Class for monitoring ArmoniK results and displaying live updates"""

    def _init_populate_watches(self):
        """Populate the watch dictionary with TaskWatch objects.

        1. Creates a `tasks_client` using the gRPC channel.
        2. If `self.entity_ids` is set, creates a `TaskWatch` for each entity ID and refreshes it.
        3. Otherwise, lists tasks from the server (using any existing filter criteria):
           - If no tasks are found and no session ID is known, prompts the user for a session ID.
           - For each listed task, creates a `TaskWatch` and stores its data.

        Raises:
            Prompt if no tasks are available and no session ID was provided.
        """
        self.tasks_client = ArmoniKTasks(self.grpc_channel)
        if self.entity_ids:
            for task_id in self.entity_ids:
                self.watches[task_id] = TaskWatch(task_id)
                self.watches[task_id].refresh(self.tasks_client)
        else:
            watchable_tasks_count, watchable_tasks = self.tasks_client.list_tasks(
                task_filter=self.filter_with,
                page=0,
                page_size=self.limit,
                sort_field=Task.created_at if self.sort_by is None else self.sort_by,
                sort_direction=Direction.ASC
                if self.sort_direction.capitalize() == "ASC"
                else Direction.DESC,
            )
            # (most likely) No session id was provided in the filter nor passed along, so we ask for it again
            if watchable_tasks_count == 0 and not self.session_id:
                self.session_id = click.prompt(
                    "No taskss available to watch, you can however specify a session and tasks that satisfy said filter within session will be watched automatically"
                )
            for task in watchable_tasks:
                self.watches[task.id] = TaskWatch(task.id)
                self.watches[task.id].data = task

    def _register_event_handlers(self):
        """Register event handlers for task updates and data refresh.

        This method spawns background threads (via `create_nonblocking_event_handler`) to listen
        for specific event types (e.g., TASK_STATUS_UPDATE) and routes them to the appropriate
        callback methods (`update_watch_status` or `refresh_task_data`). If a filter is present,
        it also registers an additional handler to automatically watch newly created tasks satisfying
        sait filter (NEW_TASK events).
        """
        self.status_update_handler = create_nonblocking_event_handler(
            self.grpc_channel,
            self.session_id,
            [EventTypes.TASK_STATUS_UPDATE],
            [self.update_watch_status],
        )
        self.task_data_refresh_handler = create_nonblocking_event_handler(
            self.grpc_channel,
            self.session_id,
            [EventTypes.TASK_STATUS_UPDATE],
            [self.refresh_task_data],
        )
        self.status_update_handler.start()
        self.task_data_refresh_handler.start()
        if (
            self.filter_with is not None
        ):  # NOTE: I think this doesn't work well for results since they're all created at the start, instead maybe look into some sort of scheduled polling until we fill?
            self.autofill_handler = create_nonblocking_event_handler(
                self.grpc_channel,
                self.session_id,
                [EventTypes.NEW_TASK],
                [self.autofill],
                task_filter=self.filter_with,
            )
            self.autofill_handler.start()

    def update_watch_status(
        self, session_id: str, event_type: EventTypes, event: TaskStatusUpdateEvent
    ) -> bool:
        """Update the status of a task when receiving a TASK_STATUS_UPDATE event.

        Args:
            session_id (str): The ID of the session for which the event applies.
            event_type (EventTypes): The type of the event (e.g., TASK_STATUS_UPDATE).
            event (TaskStatusUpdateEvent): The event data containing the updated task status.

        Returns:
            bool: Always returns False, indicating the event listener should continue running.
        """
        if event_type == EventTypes.TASK_STATUS_UPDATE and event.task_id in self.watches:
            self.watches[event.task_id].current_status = TaskStatus(event.status).name
        return False

    def refresh_task_data(
        self, session_id: str, event_type: EventTypes, event: TaskStatusUpdateEvent
    ) -> bool:
        """Refresh task data upon a TASK_STATUS_UPDATE event.

        When a task status changes, this callback triggers a refresh of the task’s
        data via the gRPC client. This ensures that the local watch’s task metadata is always
        up to date.

        Args:
            session_id (str): The ID of the session for which the event applies.
            event_type (EventTypes): The type of the event (typically TASK_STATUS_UPDATE).
            event (TaskStatusUpdateEvent): The event data containing the task ID.

        Returns:
            bool: Always returns False, indicating the event listener should continue running.
        """
        if event_type == EventTypes.TASK_STATUS_UPDATE and event.task_id in self.watches:
            self.watches[event.task_id].refresh(self.tasks_client)
        return False

    def autofill(self, session_id: str, event_type: EventTypes, event: NewTaskEvent) -> bool:
        """Callback for handling new results events to fill up the watches if we're under the limit.

        Args:
            session_id (str): The session ID associated with the event.
            event_type (EventTypes): The type of the event.
            event (NewTaskEvent): The event data containing the new task information.

        Returns:
            bool: Always returns False to not close the session.
        """
        if len(list(self.watches.keys())) < self.limit and event_type == EventTypes.NEW_TASK:
            self.watches[event.task_id] = TaskWatch(event.id)
            self.watches[event.task_id].refresh(self.tasks_client)
        return False


class TaskWatchDisplay(WatchDisplay):
    def _create_metadata_display(self):  # DOWN
        """Create a display panel for the tasks metadata.

        Returns:
            Panel: A Rich Panel containing tasks metadata.
        """
        metadata_table = Table(title="Task metadata", show_header=False, border_style="yellow")

        metadata_table.add_column("Label", style="cyan")
        metadata_table.add_column("Value")

        if self.watch.data:
            metadata_table.add_row(
                "[bold]Session ID[/bold]",
                f"[link=http://{self.endpoint}/admin/en/tasks?0-root-1-0={self.watch.data.session_id}]{self.watch.data.session_id}[/link]"
                if self.endpoint
                else self.watch.data.session_id,
            )
            metadata_table.add_row(
                "Owner Pod Id",
                f"[link=http://{self.endpoint}/seq/#/events?range=1d&filter=ownerPodId%20%3D%20'{self.watch.data.owner_pod_id}']{self.watch.data.owner_pod_id}[/link]",
            )
            metadata_table.add_row("Pod Hostname", self.watch.data.pod_hostname)
            metadata_table.add_row(
                "Data dependencies", str(self.watch.data.count_data_dependencies)
            )
            metadata_table.add_row("Outputs", str(self.watch.data.count_expected_output_ids))
            metadata_table.add_row("Status Message", self.watch.data.status_message)
        else:
            metadata_table.add_row("Data not yet retrieved")

        metadata_panel = Panel(metadata_table)
        return metadata_panel

    def _create_status_display(self):  # DOWN
        """Create a display panel for the results status.

        Returns:
            Panel: A Rich Panel containing results status.
        """
        table = Table(
            title=f"[bold]Task ID:[/bold] [link=http://{self.endpoint}/admin/en/tasks/{self.watch.id}]{self.watch.id}[/link]"
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


class TasksWatchGroupDisplay(WatchGroupDisplay):
    """Class for displaying information about monitored tasks"""

    def display(self):  # DOWN
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
            watch_display = TaskWatchDisplay(
                self.watches[self.current_tab], self.endpoint
            ).display()
        else:
            watch_display = Panel(Text("Nothing to watch.."))
        full_layout.split_column(nav_bar, Layout(watch_display, name="content"), help_bar)
        return full_layout


@tasks.command("watch")
@click.option(
    "--id",
    "task_ids",
    cls=MutuallyExclusiveOption,
    mutual=["filter_with"],
    require_one=True,
    type=str,
    default=[],
    multiple=True,
)
@click.option(
    "-f",
    "--filter",
    "filter_with",
    type=FilterParam("Task"),
    cls=MutuallyExclusiveOption,
    mutual=["task_ids"],
    require_one=True,
    required=False,
    help="An expression to filter for tasks to watch with.",
    metavar="FILTER EXPR",
)
@click.option(
    "--limit",
    cls=MutuallyExclusiveOption,
    mutual=["task_ids"],
    type=int,
    required=False,
    default=1,
    help="The maximum number of tasks to retrieve when using a filter.",
)
@click.option(
    "--session-id",
    type=str,
    required=False,
    help="Id of the session to look for the task in if none were specified in the filter",
    metavar="SESSION_ID",
)
@click.option(
    "--sort-by",
    type=FieldParam("Task"),
    required=False,
    help="Attribute of tasks to sort with, this defaults to the sorting for the most recently created tasks.",
)
@click.option(
    "--sort-direction",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    required=False,
    help="Whether to sort by ascending or by descending order.",
)
@base_command
def tasks_watch(
    endpoint: str,
    output: str,
    filter_with: Optional[TaskFilter],
    task_ids: List[str],
    limit: int,
    session_id: Optional[str],
    sort_by,
    sort_direction,
    debug: bool,
) -> None:
    """Start a watch session to get a live overview of tasks in your cluster."""
    # The TasksWatchGroup creates watches for us and spawns threads to update the different watches
    tasks_watchers = TasksWatchGroup(
        endpoint=endpoint,
        debug=debug,
        filter_with=filter_with,
        session_id=session_id,
        limit=limit,
        entity_ids=task_ids,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    tasks_display = TasksWatchGroupDisplay(tasks_watchers.get_watches_view(), endpoint)
    with Live(tasks_display.display(), refresh_per_second=10, screen=True) as live:
        while True:
            tasks_display.update()
            tasks_display.update_contents(tasks_watchers.get_watches_view())
            live.update(tasks_display.display())
    pass

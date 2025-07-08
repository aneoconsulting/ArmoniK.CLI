from datetime import timedelta
from typing import List, Optional, Tuple, Union

from armonik.client.tasks import ArmoniKTasks
from armonik.common import Task, TaskDefinition, TaskOptions, Direction
from armonik.common.filter import TaskFilter, Filter

import armonik_cli_core as akcc


@akcc.group(name="task")
def tasks(**kwargs) -> None:
    """Manage cluster's tasks."""
    pass


@tasks.command(name="list", pass_config=True, auto_output="json")
@akcc.option(
    "-f",
    "--filter",
    "filter_with",
    type=akcc.FilterParam("Task"),
    required=False,
    help="An expression to filter the listed tasks with.",
    metavar="FILTER EXPR",
)
@akcc.option(
    "--sort-by",
    type=akcc.FieldParam("Task"),
    required=False,
    help="Attribute of task to sort with.",
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
def task_list(
    config: akcc.CliConfig,
    filter_with: Union[TaskFilter, None],
    sort_by: Filter,
    sort_direction: str,
    page: int,
    page_size: int,
    **kwargs,
) -> Optional[List[Task]]:
    "List all tasks."
    with akcc.create_grpc_channel(config) as channel:
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
        return tasks_list
    return None


@tasks.command(name="get", pass_config=True, auto_output="json")
@akcc.argument("task-ids", type=str, nargs=-1, required=True)
def task_get(config: akcc.CliConfig, task_ids: List[str], **kwargs):
    """Get a detailed overview of set of tasks given their ids."""
    with akcc.create_grpc_channel(config) as channel:
        tasks_client = ArmoniKTasks(channel)
        tasks = []
        for task_id in task_ids:
            task = tasks_client.get_task(task_id)
            tasks.append(task)
        return tasks


@tasks.command(name="cancel", pass_config=True, auto_output="json")
@akcc.argument("task-ids", type=str, nargs=-1, required=True)
def task_cancel(config: akcc.CliConfig, task_ids: List[str], **kwargs):
    "Cancel tasks given their ids. (They don't have to be in the same session necessarily)."
    with akcc.create_grpc_channel(config) as channel:
        tasks_client = ArmoniKTasks(channel)
        tasks_client.cancel_tasks(task_ids)


@tasks.command(name="create", pass_config=True, auto_output="json")
@akcc.option(
    "--session-id",
    type=str,
    required=True,
    help="Id of the session to create the task in.",
    metavar="SESSION_ID",
)
@akcc.option(
    "--payload-id",
    type=str,
    required=True,
    help="Id of the payload to associated to the task.",
    metavar="PAYLOAD_ID",
)
@akcc.option(
    "--expected-outputs",
    multiple=True,
    required=True,
    help="List of the ids of the task's outputs.",
    metavar="EXPECTED_OUTPUTS",
)
@akcc.option(
    "--data-dependencies",
    multiple=True,
    help="List of the ids of the task's data dependencies.",
    metavar="DATA_DEPENDENCIES",
)
@akcc.option(
    "--max-retries",
    type=int,
    default=None,
    help="Maximum default number of execution attempts for this task.",
    metavar="NUM_RETRIES",
)
@akcc.option(
    "--max-duration",
    type=akcc.TimeDeltaParam(),
    default=None,
    help="Maximum default task execution time (format HH:MM:SS.MS).",
    metavar="DURATION",
)
@akcc.option("--priority", default=None, type=int, help="Task priority.", metavar="PRIORITY")
@akcc.option(
    "--partition-id",
    type=str,
    help="Partition to run the task in.",
    metavar="PARTITION",
)
@akcc.option(
    "--application-name",
    type=str,
    required=False,
    help="Application name for this task.",
    metavar="NAME",
)
@akcc.option(
    "--application-version",
    type=str,
    required=False,
    help="Application version for this task.",
    metavar="VERSION",
)
@akcc.option(
    "--application-namespace",
    type=str,
    required=False,
    help="Application namespace for this task.",
    metavar="NAMESPACE",
)
@akcc.option(
    "--application-service",
    type=str,
    required=False,
    help="Application service for this task.",
    metavar="SERVICE",
)
@akcc.option("--engine-type", type=str, required=False, help="Engine type.", metavar="ENGINE_TYPE")
@akcc.option(
    "--options",
    type=akcc.KeyValuePairParam(),
    default=None,
    multiple=True,
    help="Additional task options.",
    metavar="KEY=VALUE",
)
def task_create(
    config: akcc.CliConfig,
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
    **kwargs,
) -> Optional[Task]:
    """Create a task."""
    with akcc.create_grpc_channel(config) as channel:
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
            akcc.console.print(
                akcc.style(
                    "If you want to pass in additional task options please provide all three (max duration, priority, max retries)",
                    "red",
                )
            )
            raise akcc.MissingParameter(
                "If you want to pass in additional task options please provide all three (max duration, priority, max retries)"
            )
        task_definition = TaskDefinition(
            payload_id, expected_outputs, data_dependencies, task_options
        )
        submitted_tasks = tasks_client.submit_tasks(session_id, [task_definition])

        return submitted_tasks[0]

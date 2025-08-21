import armonik_cli_core as akcc
import logging
import grpc

from datetime import timedelta
from typing import List, Optional, Tuple, Union

from armonik.client.sessions import ArmoniKSessions
from armonik.common import Session, TaskOptions, Direction
from armonik.common.filter import SessionFilter, Filter


@akcc.group(name="session")
def sessions(**kwargs) -> None:
    """Manage cluster sessions."""
    pass


@sessions.command(name="list", pass_config=True, auto_output="table")
@akcc.option(
    "-f",
    "--filter",
    "filter_with",
    type=akcc.FilterParam("Session"),
    required=False,
    help="An expression to filter the sessions to be listed.",
    metavar="FILTER EXPR",
)
@akcc.option(
    "--sort-by",
    type=akcc.FieldParam("Session"),
    required=False,
    help="Attribute of session to sort with.",
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
def session_list(
    config: akcc.CliConfig,
    filter_with: Union[SessionFilter, None],
    sort_by: Filter,
    sort_direction: str,
    page: int,
    page_size: int,
    **kwargs,
) -> Optional[List[Session]]:
    """List the sessions of an ArmoniK cluster."""
    with akcc.create_grpc_channel(config) as channel:
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
        return session_list
    return None


@sessions.command(name="get", pass_config=True, auto_output="table")
@akcc.argument("session-ids", required=True, type=str, nargs=-1)
def session_get(
    config: akcc.CliConfig, session_ids: List[str], **kwargs
) -> Optional[List[Session]]:
    """Get details of a given session."""
    with akcc.create_grpc_channel(config) as channel:
        sessions_client = ArmoniKSessions(channel)
        sessions = []
        for session_id in session_ids:
            session = sessions_client.get_session(session_id=session_id)
            sessions.append(session)
        return sessions


@sessions.command(name="create", pass_config=True, auto_output="json")
@akcc.option(
    "--max-retries",
    type=int,
    default=3,
    help="Maximum default number of execution attempts for session tasks.",
    metavar="NUM_RETRIES",
)
@akcc.option(
    "--max-duration",
    type=akcc.TimeDeltaParam(),
    default="00:01:00.00",
    help="Maximum default task execution time (format HH:MM:SS.MS).",
    metavar="DURATION",
)
@akcc.option("--priority", type=int, default=1, help="Default task priority.", metavar="PRIORITY")
@akcc.option(
    "--partition",
    type=str,
    multiple=True,
    help="Partition to add to the session.",
    metavar="PARTITION",
)
@akcc.option(
    "--default-partition",
    type=str,
    default="default",
    show_default=True,
    help="Default partition.",
    metavar="PARTITION",
)
@akcc.option(
    "--application-name", type=str, required=False, help="Default application name.", metavar="NAME"
)
@akcc.option(
    "--application-version",
    type=str,
    required=False,
    help="Default application version.",
    metavar="VERSION",
)
@akcc.option(
    "--application-namespace",
    type=str,
    required=False,
    help="Default application namespace.",
    metavar="NAMESPACE",
)
@akcc.option(
    "--application-service",
    type=str,
    required=False,
    help="Default application service.",
    metavar="SERVICE",
)
@akcc.option(
    "--engine-type", type=str, required=False, help="Default engine type.", metavar="ENGINE_TYPE"
)
@akcc.option(
    "--option",
    type=akcc.KeyValuePairParam(),
    required=False,
    multiple=True,
    help="Additional default options.",
    metavar="KEY=VALUE",
)
def session_create(
    config: akcc.CliConfig,
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
    **kwargs,
) -> Optional[Session]:
    """Create a new session."""
    with akcc.create_grpc_channel(config) as channel:
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
        return session


@sessions.command(name="cancel", pass_config=True, auto_output="json")
@akcc.option(
    "--confirm",
    is_flag=True,
    help="Confirm the cancel operation on all supplied sessions all at once in advance.",
)
@akcc.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to cancel them.",
)
@akcc.argument("session-ids", required=True, type=str, nargs=-1)
def session_cancel(
    config: akcc.CliConfig,
    session_ids: List[str],
    logger: logging.Logger,
    confirm: bool,
    skip_not_found: bool,
    **kwargs,
) -> Optional[List[Session]]:
    """Cancel sessions."""
    with akcc.create_grpc_channel(config) as channel:
        sessions_client = ArmoniKSessions(channel)
        cancelled_sessions = []
        for session_id in session_ids:
            if confirm or akcc.confirm(
                f"Are you sure you want to cancel the session with id [{session_id}]",
                abort=False,
            ):
                try:
                    session = sessions_client.cancel_session(session_id=session_id)
                    cancelled_sessions.append(session)
                except grpc.RpcError as e:
                    if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                        logger.warning("Couldn't find session with id=%s, skipping...", session_id)
                        continue
                    else:
                        raise e
        return cancelled_sessions


@sessions.command(name="pause", pass_config=True, auto_output="json")
@akcc.argument("session-ids", required=True, type=str, nargs=-1)
def session_pause(
    config: akcc.CliConfig, session_ids: List[str], **kwargs
) -> Optional[List[Session]]:
    """Pause sessions."""
    with akcc.create_grpc_channel(config) as channel:
        sessions_client = ArmoniKSessions(channel)
        paused_sessions = []
        for session_id in session_ids:
            session = sessions_client.pause_session(session_id=session_id)
            paused_sessions.append(session)
        return paused_sessions


@sessions.command(name="resume", pass_config=True, auto_output="json")
@akcc.argument("session-ids", required=True, type=str, nargs=-1)
def session_resume(
    config: akcc.CliConfig, session_ids: List[str], **kwargs
) -> Optional[List[Session]]:
    """Resume sessions."""
    with akcc.create_grpc_channel(config) as channel:
        sessions_client = ArmoniKSessions(channel)
        resumed_sessions = []
        for session_id in session_ids:
            session = sessions_client.resume_session(session_id=session_id)
            resumed_sessions.append(session)
        return resumed_sessions


@sessions.command(name="close", pass_config=True, auto_output="json")
@akcc.option(
    "--confirm",
    is_flag=True,
    help="Confirm the close operation on all supplied sessions all at once in advance.",
)
@akcc.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to close them.",
)
@akcc.argument("session-ids", required=True, type=str, nargs=-1)
def session_close(
    config: akcc.CliConfig,
    logger: logging.Logger,
    session_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    **kwargs,
) -> Optional[List[Session]]:
    """Close sessions."""
    with akcc.create_grpc_channel(config) as channel:
        sessions_client = ArmoniKSessions(channel)
        closed_sessions = []
        for session_id in session_ids:
            if confirm or akcc.confirm(
                f"Are you sure you want to close the session with id [{session_id}]",
                abort=False,
            ):
                try:
                    session = sessions_client.close_session(session_id=session_id)
                    closed_sessions.append(session)
                except grpc.RpcError as e:
                    if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                        logger.warning("Couldn't find session with id=%s, skipping...", session_id)
                        continue
                    else:
                        raise e
        return closed_sessions


@sessions.command(name="purge", pass_config=True, auto_output="json")
@akcc.option(
    "--confirm",
    is_flag=True,
    help="Confirm the purge operation on all supplied sessions all at once in advance.",
)
@akcc.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to purge them.",
)
@akcc.argument("session-ids", required=True, type=str, nargs=-1)
def session_purge(
    config: akcc.CliConfig,
    logger: logging.Logger,
    session_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    **kwargs,
) -> Optional[List[Session]]:
    """Purge sessions."""
    with akcc.create_grpc_channel(config) as channel:
        sessions_client = ArmoniKSessions(channel)
        purged_sessions = []
        for session_id in session_ids:
            if confirm or akcc.confirm(
                f"Are you sure you want to purge the session with id [{session_id}]",
                abort=False,
            ):
                try:
                    session = sessions_client.purge_session(session_id=session_id)
                    purged_sessions.append(session)
                except grpc.RpcError as e:
                    if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                        logger.warning("Couldn't find session with id=%s, skipping...", session_id)
                        continue
                    else:
                        raise e

        return purged_sessions


@sessions.command(name="delete", pass_config=True, auto_output="json")
@akcc.option(
    "--confirm",
    is_flag=True,
    help="Confirm the delete operation on all supplied sessions all at once in advance.",
)
@akcc.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to delete them.",
)
@akcc.argument("session-ids", required=True, type=str, nargs=-1)
def session_delete(
    config: akcc.CliConfig,
    logger: logging.Logger,
    session_ids: List[str],
    confirm: bool,
    skip_not_found: bool,
    **kwargs,
) -> Optional[List[Session]]:
    """Delete sessions and their associated tasks from the cluster."""
    with akcc.create_grpc_channel(config) as channel:
        sessions_client = ArmoniKSessions(channel)
        deleted_sessions = []
        for session_id in session_ids:
            if confirm or akcc.confirm(
                f"Are you sure you want to delete the session with id [{session_id}]",
                abort=False,
            ):
                try:
                    session = sessions_client.delete_session(session_id=session_id)
                    deleted_sessions.append(session)
                except grpc.RpcError as e:
                    if skip_not_found and e.code() == grpc.StatusCode.NOT_FOUND:
                        logger.warning("Couldn't find session with id=%s, skipping...", session_id)
                        continue
                    else:
                        raise e
        return deleted_sessions


@sessions.command(name="stop-submission", pass_config=True, auto_output="json")
@akcc.option(
    "--clients",
    is_flag=True,
    default=False,
    help="Prevent clients from submitting new tasks in the session.",
)
@akcc.option(
    "--workers",
    is_flag=True,
    default=False,
    help="Prevent workers from submitting new tasks in the session.",
)
@akcc.option(
    "--confirm",
    is_flag=True,
    help="Confirm the block submission operation on all supplied sessions all at once in advance.",
)
@akcc.option(
    "--skip-not-found",
    is_flag=True,
    help="Skips sessions that haven't been found when trying to block submission to them.",
)
@akcc.argument("session-ids", required=True, type=str, nargs=-1)
def session_stop_submission(
    config: akcc.CliConfig,
    logger: logging.Logger,
    session_ids: str,
    confirm: bool,
    clients: bool,
    workers: bool,
    skip_not_found: bool,
    **kwargs,
) -> Optional[List[Session]]:
    """Stop clients and/or workers from submitting new tasks in a session."""
    with akcc.create_grpc_channel(config) as channel:
        sessions_client = ArmoniKSessions(channel)
        submission_blocked_sessions = []
        for session_id in session_ids:
            blocked_submitters = (
                ("clients" if clients else "")
                + (" and " if clients and workers else "")
                + ("workers" if workers else "")
            )
            if confirm or akcc.confirm(
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
                        logger.warning("Couldn't find session with id=%s, skipping...", session_id)
                        continue
                    else:
                        raise e
        return submission_blocked_sessions

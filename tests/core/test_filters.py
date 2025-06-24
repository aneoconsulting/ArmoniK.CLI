import pytest

from datetime import datetime, timedelta

from armonik.common import Partition, Result, ResultStatus, Session, SessionStatus, Task, TaskStatus
from armonik.common.filter import PartitionFilter, ResultFilter, SessionFilter, TaskFilter

from armonik_cli_core.filters import FilterParser


@pytest.mark.parametrize(
    ("args", "expr", "filter"),
    [
        ((Session, SessionFilter, SessionStatus), "session_id = id", Session.session_id == "id"),
        ((Session, SessionFilter, SessionStatus), "session_id != id", Session.session_id != "id"),
        (
            (Session, SessionFilter, SessionStatus),
            "session_id startswith id",
            Session.session_id.startswith("id"),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "session_id endswith id",
            Session.session_id.endswith("id"),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "session_id contains id",
            Session.session_id.contains("id"),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "session_id notcontains id",
            -Session.session_id.contains("id"),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "status = running",
            Session.status == SessionStatus.RUNNING,
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "status != running",
            Session.status != SessionStatus.RUNNING,
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "client_submission is true",
            Session.client_submission,
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "client_submission is false",
            -Session.client_submission,
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "partition_ids contains default",
            Session.partition_ids.contains("default"),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "partition_ids notcontains default",
            -Session.partition_ids.contains("default"),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "duration = 1:00:00",
            Session.duration == timedelta(hours=1),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "duration = 15:00:00.10",
            Session.duration == timedelta(hours=15, milliseconds=100),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "duration > 15:00:00.10",
            Session.duration > timedelta(hours=15, milliseconds=100),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "created_at = 2024-12-28",
            Session.created_at == datetime(year=2024, month=12, day=28),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "created_at = 2024-12-28T23:00:15",
            Session.created_at
            == datetime(year=2024, month=12, day=28, hour=23, minute=0, second=15),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "created_at != 2024-12-28T23:00:15",
            Session.created_at
            != datetime(year=2024, month=12, day=28, hour=23, minute=0, second=15),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "created_at > 2024-12-28T23:00:15",
            Session.created_at
            > datetime(year=2024, month=12, day=28, hour=23, minute=0, second=15),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "created_at >= 2024-12-28T23:00:15",
            Session.created_at
            >= datetime(year=2024, month=12, day=28, hour=23, minute=0, second=15),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "created_at < 2024-12-28T23:00:15",
            Session.created_at
            < datetime(year=2024, month=12, day=28, hour=23, minute=0, second=15),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "created_at <= 2024-12-28T23:00:15",
            Session.created_at
            <= datetime(year=2024, month=12, day=28, hour=23, minute=0, second=15),
        ),
        (
            (Session, SessionFilter, SessionStatus, True),
            "options.application_name = name",
            Session.options.application_name == "name",
        ),
        (
            (Session, SessionFilter, SessionStatus, True),
            "options.priority = 1",
            Session.options.priority == 1,
        ),
        (
            (Session, SessionFilter, SessionStatus, True),
            "options[key] = value",
            Session.options["key"] == "value",
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "session_id = id and status != running",
            (Session.session_id == "id") & (Session.status != SessionStatus.RUNNING),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "session_id = id or status != running",
            (Session.session_id == "id") | (Session.status != SessionStatus.RUNNING),
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "session_id = id and status != running or session_id startswith ok",
            (Session.session_id == "id") & (Session.status != SessionStatus.RUNNING)
            | (Session.session_id.startswith("ok")),
        ),
        (
            (Result, ResultFilter, ResultStatus),
            "size >= 5000",
            Result.size >= 5000,
        ),
        (
            (Task, TaskFilter, TaskStatus),
            "owner_pod_id = pod-id",
            Task.owner_pod_id == "pod-id",
        ),
        (
            (Task, TaskFilter, TaskStatus, True),
            "options.application_name = app_name",
            Task.options.application_name == "app_name",
        ),
        (
            (Task, TaskFilter, TaskStatus, True),
            "options.application_name = ''",
            Task.options.application_name == "",
        ),
        (
            (Task, TaskFilter, TaskStatus, True, True),
            "output.error contains 'an error occured'",
            Task.output.error.contains("an error occured"),
        ),
        (
            (Partition, PartitionFilter),
            "priority = 1",
            Partition.priority == 1,
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "client_submission",
            Session.client_submission,
        ),
        (
            (Session, SessionFilter, SessionStatus),
            "not client_submission",
            -Session.client_submission,
        ),
        (
            (Session, SessionFilter, SessionStatus),
            '!(client_submission AND session_id = "id")',
            -(Session.client_submission & (Session.session_id == "id")),
        ),
    ],
)
def test_filter_parser(args, expr, filter):
    assert FilterParser(*args).parse(expr).to_dict() == filter.to_dict()

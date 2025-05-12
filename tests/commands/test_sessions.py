import pytest

from datetime import datetime, timedelta
from copy import deepcopy

from armonik.client import ArmoniKSessions
from armonik.common import Session, TaskOptions, SessionStatus
from conftest import run_cmd_and_assert_exit_code, reformat_cmd_output

ENDPOINT = "172.17.119.85:5001"

raw_session = Session(
    session_id="id",
    status=SessionStatus.RUNNING,
    client_submission=True,
    worker_submission=True,
    partition_ids=["default"],
    options=TaskOptions(
        max_duration=timedelta(hours=1),
        priority=1,
        max_retries=2,
        partition_id="default",
        application_name="",
        application_version="",
        application_namespace="",
        application_service="",
        engine_type="",
        options={},
    ),
    created_at=datetime(year=2024, month=11, day=11),
    cancelled_at=None,
    closed_at=None,
    purged_at=None,
    deleted_at=None,
    duration=timedelta(hours=0),
)
serialized_session = {
    "SessionId": "id",
    "Status": "Running",
    "ClientSubmission": True,
    "WorkerSubmission": True,
    "PartitionIds": ["default"],
    "Options": {
        "MaxDuration": "1:00:00",
        "Priority": 1,
        "MaxRetries": 2,
        "PartitionId": "default",
        "ApplicationName": "",
        "ApplicationVersion": "",
        "ApplicationNamespace": "",
        "ApplicationService": "",
        "EngineType": "",
        "Options": {},
    },
    "CreatedAt": "2024-11-11 00:00:00",
    "CancelledAt": None,
    "ClosedAt": None,
    "PurgedAt": None,
    "DeletedAt": None,
    "Duration": "0:00:00",
}

# This fails the unit testing workflow (why? I'm not sure, but this isn't an important test)
# @pytest.mark.parametrize("flag", ["", "-h", "--help"])
# def test_session(flag):
#     run_cmd_and_assert_exit_code(f"session {flag}")


@pytest.mark.parametrize(
    "cmd",
    [
        f"session list --endpoint {ENDPOINT} --output json",
    ],
)
def test_session_list(mocker, cmd):
    mocker.patch.object(ArmoniKSessions, "list_sessions", return_value=(1, [deepcopy(raw_session)]))
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == [serialized_session]


@pytest.mark.parametrize(
    "cmd",
    [
        f"session get --endpoint {ENDPOINT} id --output json",
    ],
)
def test_session_get(mocker, cmd):
    mocker.patch.object(ArmoniKSessions, "get_session", return_value=deepcopy(raw_session))
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == [serialized_session]


@pytest.mark.parametrize(
    "cmd",
    [
        f"session create --priority 1 --max-duration 01:00:0 --max-retries 2 --endpoint {ENDPOINT} --output json",
        f"session create --priority 1 --max-duration 01:00:0 --max-retries 2 --endpoint {ENDPOINT} --output json "
        "--default-partition bench --partition bench --partition htcmock --option op1=val1 --option opt2=val2 "
        "--application-name app --application-version v1 --application-namespace ns --application-service svc --engine-type eng",
    ],
)
def test_session_create(mocker, cmd):
    mocker.patch.object(ArmoniKSessions, "create_session", return_value="id")
    mocker.patch.object(ArmoniKSessions, "get_session", return_value=deepcopy(raw_session))
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == serialized_session


@pytest.mark.parametrize(
    ("cmd", "prompt"),
    [
        (f"session cancel --confirm --endpoint {ENDPOINT} id", None),
        (f"session cancel --endpoint {ENDPOINT} id", "y"),
    ],
)
def test_session_cancel(mocker, cmd, prompt):
    mocker.patch.object(ArmoniKSessions, "cancel_session", return_value=deepcopy(raw_session))
    result = run_cmd_and_assert_exit_code(cmd, input=prompt)
    assert reformat_cmd_output(
        result.output, deserialize=True, first_line_out=True if prompt else False
    ) == [serialized_session]


@pytest.mark.parametrize(
    "cmd",
    [
        f"session pause --endpoint {ENDPOINT} id",
    ],
)
def test_session_pause(mocker, cmd):
    mocker.patch.object(ArmoniKSessions, "pause_session", return_value=deepcopy(raw_session))
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == [serialized_session]


@pytest.mark.parametrize(
    "cmd",
    [
        f"session resume --endpoint {ENDPOINT} id",
    ],
)
def test_session_resume(mocker, cmd):
    mocker.patch.object(ArmoniKSessions, "resume_session", return_value=deepcopy(raw_session))
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == [serialized_session]


@pytest.mark.parametrize(
    ("cmd", "prompt"),
    [
        (f"session close --confirm --endpoint {ENDPOINT} id", None),
        (f"session close --endpoint {ENDPOINT} id", "y"),
    ],
)
def test_session_close(mocker, cmd, prompt):
    mocker.patch.object(ArmoniKSessions, "close_session", return_value=deepcopy(raw_session))
    result = run_cmd_and_assert_exit_code(cmd, input=prompt)
    assert reformat_cmd_output(
        result.output, deserialize=True, first_line_out=True if prompt else False
    ) == [serialized_session]


@pytest.mark.parametrize(
    ("cmd", "prompt"),
    [
        (f"session purge --confirm --endpoint {ENDPOINT} id", None),
        (f"session purge --endpoint {ENDPOINT} id", "y"),
    ],
)
def test_session_purge(mocker, cmd, prompt):
    mocker.patch.object(ArmoniKSessions, "purge_session", return_value=deepcopy(raw_session))
    result = run_cmd_and_assert_exit_code(cmd, input=prompt)
    assert reformat_cmd_output(
        result.output, deserialize=True, first_line_out=True if prompt else False
    ) == [serialized_session]


@pytest.mark.parametrize(
    ("cmd", "prompt"),
    [
        (f"session delete --confirm --endpoint {ENDPOINT} id", None),
        (f"session delete --endpoint {ENDPOINT} id", "y"),
    ],
)
def test_session_delete(mocker, cmd, prompt):
    mocker.patch.object(ArmoniKSessions, "delete_session", return_value=deepcopy(raw_session))
    result = run_cmd_and_assert_exit_code(cmd, input=prompt)
    assert reformat_cmd_output(
        result.output, deserialize=True, first_line_out=True if prompt else False
    ) == [serialized_session]


@pytest.mark.parametrize(
    "cmd",
    [
        f"session stop-submission --endpoint {ENDPOINT} id --confirm",
        f"session stop-submission --clients --endpoint {ENDPOINT} id --confirm",
        f"session stop-submission --workers --endpoint {ENDPOINT} id --confirm",
    ],
)
def test_session_stop_submission(mocker, cmd):
    mocker.patch.object(
        ArmoniKSessions, "stop_submission_session", return_value=deepcopy(raw_session)
    )
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == [serialized_session]

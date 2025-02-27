from copy import deepcopy
from datetime import datetime, timedelta
import pytest

from armonik.client import ArmoniKTasks
from armonik.common import Task, TaskOptions, TaskStatus

from conftest import run_cmd_and_assert_exit_code, reformat_cmd_output


ENDPOINT = "172.17.119.85:5001"

raw_tasks = [
    Task(
        id="fd07e705-57bc-415c-9bd6-dd07f333a126",
        session_id="a9ae4a53-44f1-40a9-b91e-2ccd9f148f50",
        owner_pod_id="10.42.0.59",
        initial_task_id="fd07e705-57bc-415c-9bd6-dd07f333a126",
        created_by="9f8a5c21-b606-43c1-8fed-f588a22a97ed",
        parent_task_ids=[
            "a9ae4a53-44f1-40a9-b91e-2ccd9f148f50",
            "9f8a5c21-b606-43c1-8fed-f588a22a97ed",
        ],
        data_dependencies=[],
        expected_output_ids=["6205a751-36a0-481a-aaab-d1d052721935"],
        retry_of_ids=[],
        status=TaskStatus.COMPLETED,
        options=TaskOptions(
            max_duration=timedelta(hours=1),
            priority=1,
            max_retries=2,
            partition_id="htcmock",
            application_name="",
            application_version="",
            application_namespace="",
            application_service="",
            engine_type="",
            options={
                "UseLowMem": True,
                "TaskError": "",
                "FastCompute": True,
                "SmallOutput": True,
                "TaskRpcException": "",
            },
        ),
        created_at=datetime(year=2024, month=11, day=11),
        submitted_at=datetime(year=2024, month=11, day=11),
        received_at=datetime(year=2024, month=11, day=11),
        fetched_at=datetime(year=2024, month=11, day=11),
        started_at=datetime(year=2024, month=11, day=11),
        processed_at=datetime(year=2024, month=11, day=11),
        ended_at=datetime(year=2024, month=11, day=11),
        pod_ttl=datetime(year=2024, month=11, day=11),
        creation_to_end_duration=timedelta(hours=0),
        received_to_end_duration=timedelta(hours=0),
        output=None,
        pod_hostname="compute-plane-htcmock-78d5745574-6bf9k",
        payload_id="7cb7e0ca-6f9b-4e3e-9d13-87c42b876bd4",
    ),
    Task(
        id="ffe3d080-b0b4-4c7b-a569-b89cdf639f40",
        session_id="a9ae4a53-44f1-40a9-b91e-2ccd9f148f50",
        owner_pod_id="10.42.0.59",
        initial_task_id="ffe3d080-b0b4-4c7b-a569-b89cdf639f40",
        created_by="9f8a5c21-b606-43c1-8fed-f588a22a97ed",
        parent_task_ids=[
            "a9ae4a53-44f1-40a9-b91e-2ccd9f148f50",
            "9f8a5c21-b606-43c1-8fed-f588a22a97ed",
        ],
        data_dependencies=[],
        expected_output_ids=["25f69d02-20f1-49db-b6b9-c82cce4e35ac"],
        retry_of_ids=[],
        status=TaskStatus.COMPLETED,
        options=TaskOptions(
            max_duration=timedelta(hours=1),
            priority=1,
            max_retries=2,
            partition_id="htcmock",
            application_name="",
            application_version="",
            application_namespace="",
            application_service="",
            engine_type="",
            options={
                "UseLowMem": True,
                "TaskError": "",
                "FastCompute": True,
                "SmallOutput": True,
                "TaskRpcException": "",
            },
        ),
        created_at=datetime(year=2024, month=11, day=11),
        submitted_at=datetime(year=2024, month=11, day=11),
        received_at=datetime(year=2024, month=11, day=11),
        fetched_at=datetime(year=2024, month=11, day=11),
        started_at=datetime(year=2024, month=11, day=11),
        processed_at=datetime(year=2024, month=11, day=11),
        ended_at=datetime(year=2024, month=11, day=11),
        pod_ttl=datetime(year=2024, month=11, day=11),
        creation_to_end_duration=timedelta(hours=0),
        received_to_end_duration=timedelta(hours=0),
        output=None,
        pod_hostname="compute-plane-htcmock-78d5745574-6bf9k",
        payload_id="8a3e2125-f382-4462-9d97-46e874c10851",
    ),
]

serialized_tasks = [
    {
        "Id": "fd07e705-57bc-415c-9bd6-dd07f333a126",
        "SessionId": "a9ae4a53-44f1-40a9-b91e-2ccd9f148f50",
        "OwnerPodId": "10.42.0.59",
        "InitialTaskId": "fd07e705-57bc-415c-9bd6-dd07f333a126",
        "CreatedBy": "9f8a5c21-b606-43c1-8fed-f588a22a97ed",
        "ParentTaskIds": [
            "a9ae4a53-44f1-40a9-b91e-2ccd9f148f50",
            "9f8a5c21-b606-43c1-8fed-f588a22a97ed",
        ],
        "DataDependencies": [],
        "ExpectedOutputIds": ["6205a751-36a0-481a-aaab-d1d052721935"],
        "RetryOfIds": [],
        "Status": "Completed",
        "StatusMessage": None,
        "Options": {
            "MaxDuration": "1:00:00",
            "Priority": 1,
            "MaxRetries": 2,
            "PartitionId": "htcmock",
            "ApplicationName": "",
            "ApplicationVersion": "",
            "ApplicationNamespace": "",
            "ApplicationService": "",
            "EngineType": "",
            "Options": {
                "UseLowMem": True,
                "TaskError": "",
                "FastCompute": True,
                "SmallOutput": True,
                "TaskRpcException": "",
            },
        },
        "CreatedAt": "2024-11-11 00:00:00",
        "SubmittedAt": "2024-11-11 00:00:00",
        "ReceivedAt": "2024-11-11 00:00:00",
        "AcquiredAt": None,
        "FetchedAt": "2024-11-11 00:00:00",
        "StartedAt": "2024-11-11 00:00:00",
        "ProcessedAt": "2024-11-11 00:00:00",
        "EndedAt": "2024-11-11 00:00:00",
        "PodTtl": "2024-11-11 00:00:00",
        "CreationToEndDuration": "0:00:00",
        "ProcessingToEndDuration": "0:00:00",
        "ReceivedToEndDuration": "0:00:00",
        "Output": None,
        "PodHostname": "compute-plane-htcmock-78d5745574-6bf9k",
        "PayloadId": "7cb7e0ca-6f9b-4e3e-9d13-87c42b876bd4",
    },
    {
        "Id": "ffe3d080-b0b4-4c7b-a569-b89cdf639f40",
        "SessionId": "a9ae4a53-44f1-40a9-b91e-2ccd9f148f50",
        "OwnerPodId": "10.42.0.59",
        "InitialTaskId": "ffe3d080-b0b4-4c7b-a569-b89cdf639f40",
        "CreatedBy": "9f8a5c21-b606-43c1-8fed-f588a22a97ed",
        "ParentTaskIds": [
            "a9ae4a53-44f1-40a9-b91e-2ccd9f148f50",
            "9f8a5c21-b606-43c1-8fed-f588a22a97ed",
        ],
        "DataDependencies": [],
        "ExpectedOutputIds": ["25f69d02-20f1-49db-b6b9-c82cce4e35ac"],
        "RetryOfIds": [],
        "Status": "Completed",
        "StatusMessage": None,
        "Options": {
            "MaxDuration": "1:00:00",
            "Priority": 1,
            "MaxRetries": 2,
            "PartitionId": "htcmock",
            "ApplicationName": "",
            "ApplicationVersion": "",
            "ApplicationNamespace": "",
            "ApplicationService": "",
            "EngineType": "",
            "Options": {
                "UseLowMem": True,
                "TaskError": "",
                "FastCompute": True,
                "SmallOutput": True,
                "TaskRpcException": "",
            },
        },
        "CreatedAt": "2024-11-11 00:00:00",
        "SubmittedAt": "2024-11-11 00:00:00",
        "ReceivedAt": "2024-11-11 00:00:00",
        "AcquiredAt": None,
        "FetchedAt": "2024-11-11 00:00:00",
        "StartedAt": "2024-11-11 00:00:00",
        "ProcessedAt": "2024-11-11 00:00:00",
        "EndedAt": "2024-11-11 00:00:00",
        "PodTtl": "2024-11-11 00:00:00",
        "CreationToEndDuration": "0:00:00",
        "ProcessingToEndDuration": "0:00:00",
        "ReceivedToEndDuration": "0:00:00",
        "Output": None,
        "PodHostname": "compute-plane-htcmock-78d5745574-6bf9k",
        "PayloadId": "8a3e2125-f382-4462-9d97-46e874c10851",
    },
]


@pytest.mark.parametrize("cmd", [f"task list -e {ENDPOINT} --output json"])
def test_task_list(mocker, cmd):
    mocker.patch.object(ArmoniKTasks, "list_tasks", return_value=(2, deepcopy(raw_tasks)))
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == serialized_tasks


@pytest.mark.parametrize(
    "cmd, expected_outputs",
    [
        (
            f"task get --endpoint {ENDPOINT} --output json {serialized_tasks[0]['Id']}",
            [serialized_tasks[0]],
        ),
        (
            f"task get --endpoint {ENDPOINT} --output json {serialized_tasks[0]['Id']} {serialized_tasks[1]['Id']}",
            serialized_tasks,
        ),
    ],
)
def test_task_get(mocker, cmd, expected_outputs):
    def get_task_side_effect(task_id):
        if task_id == serialized_tasks[0]["Id"]:
            return deepcopy(raw_tasks[0])
        elif task_id == serialized_tasks[1]["Id"]:
            return deepcopy(raw_tasks[1])

    mocker.patch.object(ArmoniKTasks, "get_task", side_effect=get_task_side_effect)
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == expected_outputs


@pytest.mark.parametrize(
    "cmd",
    [
        f"task cancel --endpoint {ENDPOINT} {serialized_tasks[0]['Id']}",
        f"task cancel --endpoint {ENDPOINT} {serialized_tasks[0]['Id']} {serialized_tasks[1]['Id']}",
    ],
)
def test_task_cancel(mocker, cmd):
    mocker.patch.object(ArmoniKTasks, "cancel_tasks", return_value=None)
    run_cmd_and_assert_exit_code(cmd)


@pytest.mark.parametrize(
    "cmd, exit_code",
    [
        (
            f"task create --endpoint {ENDPOINT} --session-id sessionid --payload-id payloadid --expected-outputs 1 --expected-outputs 2 --data-dependencies 3",
            0,
        ),
        (
            f"task create --endpoint {ENDPOINT} --session-id sessionid --payload-id payloadid --expected-outputs 1 --expected-outputs 2 --data-dependencies 3 --max-duration 00:00:15.00 --priority 1 --max-retries 2",
            0,
        ),
        (
            f"task create --endpoint {ENDPOINT} --session-id sessionid --payload-id payloadid --expected-outputs 1 --expected-outputs 2 --data-dependencies 3 --max-duration 00:00:15.00 --priority 0",
            3,
        ),
    ],
)
def test_task_create(mocker, cmd, exit_code):
    mocker.patch.object(ArmoniKTasks, "submit_tasks", return_value=[deepcopy(raw_tasks[0])])
    run_cmd_and_assert_exit_code(cmd, exit_code=exit_code)

from dataclasses import dataclass
from enum import IntEnum
import pytest

from datetime import timedelta, datetime

from armonik.common import Session, TaskOptions, SessionStatus, Task, TaskStatus, Partition

from armonik_cli_core.serialize import serialize


# Helper classes and functions for testing
class MyEnum(IntEnum):
    FIRST = 1
    SECOND = 2


@dataclass
class SimpleDataClass:
    name: str
    value: int


class RegularClass:
    def __init__(self, title: str, count: int):
        self.title = title
        self.count = count


def test_primitive_types():
    """Test serialization of primitive types"""
    assert serialize("test") == "test"
    assert serialize(123) == 123
    assert serialize(3.14) == 3.14
    assert serialize(True)
    assert serialize({"key": "value"}) == {"key": "value"}
    assert serialize(None) is None


def test_datetime():
    """Test serialization of datetime objects"""
    assert serialize(datetime(2024, 1, 1, 12, 0)) == "2024-01-01 12:00:00"
    assert serialize(datetime(2024, 1, 1, 12, 30, 45, 80)) == "2024-01-01 12:30:45.000080"


def test_timedelta():
    """Test serialization of timedelta objects"""
    td = timedelta(days=1, hours=2)
    assert serialize(td) == str(td)


def test_list():
    """Test serialization of lists"""
    test_list = [1, "test", True]
    assert serialize(test_list) == test_list


def test_dict():
    """Test serialization of dicts"""
    test_dict = {"time": datetime(2024, 1, 1, 12, 0), "enum": MyEnum.FIRST}
    assert serialize(test_dict) == {"time": "2024-01-01 12:00:00", "enum": "First"}


def test_nested_list():
    """Test serialization of nested lists"""
    nested_list = [1, ["a", "b"], {"key": "value"}]
    assert serialize(nested_list) == nested_list


def test_enum():
    """Test serialization of IntEnum"""
    assert serialize(MyEnum.FIRST) == "First"
    assert serialize(MyEnum.SECOND) == "Second"


def test_dataclass():
    """Test serialization of dataclass"""
    dc = SimpleDataClass(name="test", value=42)
    expected = {"Name": "test", "Value": 42}  # serializer capitalizes field names
    assert serialize(dc) == expected


def test_regular_class():
    """Test serialization of regular class"""
    obj = RegularClass(title="test", count=42)
    expected = {"Title": "test", "Count": 42}
    assert serialize(obj) == expected


def test_complex_nested_structure():
    """Test serialization of complex nested structure"""

    @dataclass
    class ComplexData:
        enum_value: MyEnum
        dates: list[datetime]
        nested: SimpleDataClass

    dt1 = datetime(2024, 1, 1)
    dt2 = datetime(2024, 1, 2)
    complex_obj = ComplexData(
        enum_value=MyEnum.FIRST, dates=[dt1, dt2], nested=SimpleDataClass(name="nested", value=99)
    )

    expected = {
        "EnumValue": "First",
        "Dates": ["2024-01-01 00:00:00", "2024-01-02 00:00:00"],
        "Nested": {"Name": "nested", "Value": 99},
    }
    assert serialize(complex_obj) == expected


def test_empty_structures():
    """Test serialization of empty structures"""
    assert serialize([]) == []
    assert serialize({}) == {}

    @dataclass
    class EmptyDataClass:
        pass

    assert serialize(EmptyDataClass()) == {}


def test_invalid_input():
    """Test handling of potentially problematic inputs"""

    class NoAnnotationsClass:
        def __init__(self):
            self.value = 42

    assert serialize(NoAnnotationsClass) == {}


@pytest.mark.parametrize(
    "raw_input, serialized_output",
    [
        (
            Session(
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
            ),
            {
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
            },
        )
    ],
)
def test_serializer_success_session(raw_input, serialized_output):
    """Test serialization for Session objects."""
    assert serialize(raw_input) == serialized_output


@pytest.mark.parametrize(
    "raw_input, serialized_output",
    [
        (
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
        )
    ],
)
def test_serializer_success_task(raw_input, serialized_output):
    """Test serialization for Task objects."""
    assert serialize(raw_input) == serialized_output


@pytest.mark.parametrize(
    "raw_input, serialized_output",
    [
        (
            Partition(
                id="stream",
                parent_partition_ids=[],
                pod_reserved=1,
                pod_max=100,
                pod_configuration={},
                preemption_percentage=50,
                priority=1,
            ),
            {
                "Id": "stream",
                "ParentPartitionIds": [],
                "PodReserved": 1,
                "PodMax": 100,
                "PodConfiguration": {},
                "PreemptionPercentage": 50,
                "Priority": 1,
            },
        )
    ],
)
def test_serializer_success_partition(raw_input, serialized_output):
    """Test serialization for Partition objects."""
    assert serialize(raw_input) == serialized_output

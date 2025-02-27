from copy import deepcopy
import pytest

from armonik.client import ArmoniKPartitions
from armonik.common import Partition

from conftest import run_cmd_and_assert_exit_code, reformat_cmd_output

ENDPOINT = "172.17.119.85:5001"


raw_partitions = [
    Partition(
        id="stream",
        parent_partition_ids=[],
        pod_reserved=1,
        pod_max=100,
        pod_configuration={},
        preemption_percentage=50,
        priority=1,
    ),
    Partition(
        id="bench",
        parent_partition_ids=[],
        pod_reserved=1,
        pod_max=100,
        pod_configuration={},
        preemption_percentage=50,
        priority=1,
    ),
]

serialized_partitions = [
    {
        "Id": "stream",
        "ParentPartitionIds": [],
        "PodReserved": 1,
        "PodMax": 100,
        "PodConfiguration": {},
        "PreemptionPercentage": 50,
        "Priority": 1,
    },
    {
        "Id": "bench",
        "ParentPartitionIds": [],
        "PodReserved": 1,
        "PodMax": 100,
        "PodConfiguration": {},
        "PreemptionPercentage": 50,
        "Priority": 1,
    },
]


@pytest.mark.parametrize("cmd", [f"partition list -e {ENDPOINT} --output json"])
def test_partition_list(mocker, cmd):
    mocker.patch.object(
        ArmoniKPartitions,
        "list_partitions",
        return_value=(len(raw_partitions), deepcopy(raw_partitions)),
    )
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == serialized_partitions


@pytest.mark.parametrize(
    "cmd, expected_output",
    [
        (
            f"partition get --endpoint {ENDPOINT} --output json {serialized_partitions[0]['Id']}",
            [serialized_partitions[0]],
        ),
        (
            f"partition get --endpoint {ENDPOINT} --output json {serialized_partitions[0]['Id']} {serialized_partitions[1]['Id']}",
            [serialized_partitions[0], serialized_partitions[1]],
        ),
    ],
)
def test_partition_get(mocker, cmd, expected_output):
    def get_partitions_side_effect(partition_id):
        if partition_id == serialized_partitions[0]["Id"]:
            return deepcopy(raw_partitions[0])
        elif partition_id == serialized_partitions[1]["Id"]:
            return deepcopy(raw_partitions[1])

    mocker.patch.object(ArmoniKPartitions, "get_partition", side_effect=get_partitions_side_effect)
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == expected_output

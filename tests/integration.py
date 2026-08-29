import json
import re

import pytest
import grpc

from conftest import run_cmd_and_assert_exit_code

from armonik.client.results import ArmoniKResults

ENDPOINT = "172.17.63.166:5001"

ansi_codes = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def remove_ansi_escapecodes(in_string: str) -> str:
    return ansi_codes.sub("", in_string)


@pytest.fixture(scope="session")
def context():
    return {"created_session_id": None, "created_result_ids": [], "created_task_ids": []}


@pytest.mark.dependency(name="create_session")
def test_create_session(context):
    # Note: we're not testing the serialization here, but more so the interaction of the CLI with the ArmoniK API, hence the nature of this test
    create_session_result = run_cmd_and_assert_exit_code(
        f"session create --priority 1 --max-duration 01:00:0 --max-retries 2 --endpoint {ENDPOINT}"
    )

    deserialized_created_session = json.loads(remove_ansi_escapecodes(create_session_result.output))
    # Convert result to dict
    assert "SessionId" in deserialized_created_session
    get_session_result = run_cmd_and_assert_exit_code(
        f"session get --endpoint {ENDPOINT} {deserialized_created_session['SessionId']}"
    )
    deserialized_get_session = json.loads(remove_ansi_escapecodes(get_session_result.output))
    assert deserialized_created_session == deserialized_get_session
    context["created_session_id"] = deserialized_get_session["SessionId"]


@pytest.mark.dependency(name="create_result", depends=["create_session"])
def test_create_result():
    pass


@pytest.mark.dependency(name="create_task", depends=["create_result"])
def test_create_task(context):
    # Ideally we'd create the results for payload, expected_output in a step before but since we don't have results merged yet this will do
    created_session_id = context["created_session_id"]
    grpc_channel = grpc.insecure_channel(ENDPOINT)
    results_client = ArmoniKResults(grpc_channel)
    result_objects = results_client.create_results_metadata(
        [f"payload-{created_session_id}", f"output-{created_session_id}"], created_session_id
    )
    payload_id = result_objects[f"payload-{created_session_id}"].result_id
    expected_output_id = result_objects[f"output-{created_session_id}"].result_id
    context["created_result_ids"] = [payload_id, expected_output_id]
    create_task_result = run_cmd_and_assert_exit_code(
        f"task create --endpoint {ENDPOINT} --session-id {created_session_id} --payload-id {payload_id} --expected-outputs {expected_output_id} --debug"
    )
    deserialized_created_task = json.loads(remove_ansi_escapecodes(create_task_result.output))
    context["created_task_ids"] = [deserialized_created_task["Id"]]
    get_task_result = run_cmd_and_assert_exit_code(
        f"task get --endpoint {ENDPOINT} {deserialized_created_task['Id']}"
    )
    deserialized_get_task = json.loads(remove_ansi_escapecodes(get_task_result.output))

    assert deserialized_created_task["Id"] == deserialized_get_task[0]["Id"]


@pytest.mark.dependency(name="cleanup", depends=["create_task"])
def test_cleanup(context):
    # Delete session and tasks in it (I can never actually delete the results..)
    delete_session_result = run_cmd_and_assert_exit_code(
        f"session delete --endpoint {ENDPOINT} {context['created_session_id']} --confirm"
    )
    assert "error" not in delete_session_result.output.lower()

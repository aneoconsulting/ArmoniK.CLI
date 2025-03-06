from copy import deepcopy
from datetime import datetime
import pathlib
from unittest.mock import Mock, mock_open
import pytest

from armonik.client.results import ArmoniKResults
from armonik.common import Result, ResultStatus

from conftest import run_cmd_and_assert_exit_code, reformat_cmd_output

ENDPOINT = "172.17.119.85:5001"

raw_results = [
    Result(
        session_id="5f723ff6-56e7-4329-a5d1-5e1f7ba6c7ef",
        name="",
        created_by="37b15f70-cacc-4ffd-8cbd-e5986f7edbb4",
        owner_task_id="",
        status=ResultStatus.DELETED,
        created_at=datetime(year=2025, month=1, day=15),
        completed_at=None,
        result_id="e9cb3a53-e742-4ea5-b66b-8a0f9eb1f49d",
        size=20910,
        opaque_id="",
    ),
    Result(
        session_id="5f723ff6-56e7-4329-a5d1-5e1f7ba6c7ef",
        name="",
        created_by="37b15f70-cacc-4ffd-8cbd-e5986f7edbb4",
        owner_task_id="",
        status=ResultStatus.DELETED,
        created_at=datetime(year=2025, month=1, day=15),
        completed_at=None,
        result_id="cb0c7a4a-d7e7-4bea-bb0e-66c3628f9ac3",
        size=20942,
        opaque_id="",
    ),
]

serialized_results = [
    {
        "SessionId": "5f723ff6-56e7-4329-a5d1-5e1f7ba6c7ef",
        "Name": "",
        "CreatedBy": "37b15f70-cacc-4ffd-8cbd-e5986f7edbb4",
        "OpaqueId": "",
        "OwnerTaskId": "",
        "Status": "Deleted",
        "CreatedAt": "2025-01-15 00:00:00",
        "CompletedAt": None,
        "ResultId": "e9cb3a53-e742-4ea5-b66b-8a0f9eb1f49d",
        "Size": 20910,
    },
    {
        "SessionId": "5f723ff6-56e7-4329-a5d1-5e1f7ba6c7ef",
        "Name": "",
        "CreatedBy": "37b15f70-cacc-4ffd-8cbd-e5986f7edbb4",
        "OpaqueId": "",
        "OwnerTaskId": "",
        "Status": "Deleted",
        "CreatedAt": "2025-01-15 00:00:00",
        "CompletedAt": None,
        "ResultId": "cb0c7a4a-d7e7-4bea-bb0e-66c3628f9ac3",
        "Size": 20942,
    },
]


@pytest.mark.parametrize("cmd", [f"result list -e {ENDPOINT} --output json -f session_id=id"])
def test_result_list(mocker, cmd):
    mocker.patch.object(ArmoniKResults, "list_results", return_value=(2, deepcopy(raw_results)))
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == serialized_results


@pytest.mark.parametrize(
    "cmd, expected_output",
    [
        (
            f"result get --endpoint {ENDPOINT} --output json {serialized_results[0]['ResultId']}",
            [serialized_results[0]],
        ),
        (
            f"result get --endpoint {ENDPOINT} --output json {serialized_results[0]['ResultId']} {serialized_results[1]['ResultId']}",
            [serialized_results[0], serialized_results[1]],
        ),
    ],
)
def test_result_get(mocker, cmd, expected_output):
    def get_result_side_effect(result_id):
        if result_id == serialized_results[0]["ResultId"]:
            return deepcopy(raw_results[0])
        elif result_id == serialized_results[1]["ResultId"]:
            return deepcopy(raw_results[1])

    mocker.patch.object(ArmoniKResults, "get_result", side_effect=get_result_side_effect)
    result = run_cmd_and_assert_exit_code(cmd)
    assert reformat_cmd_output(result.output, deserialize=True) == expected_output


@pytest.mark.parametrize(
    "cmd, expected_output",
    [
        (
            f"result delete-data --endpoint {ENDPOINT} {serialized_results[0]['ResultId']} --confirm --debug",
            {serialized_results[0]["SessionId"]: [serialized_results[0]["ResultId"]]},
        ),
        (
            f"result delete-data --endpoint {ENDPOINT} {serialized_results[0]['ResultId']} {serialized_results[1]['ResultId']} --confirm --debug",
            {
                serialized_results[0]["SessionId"]: [
                    serialized_results[0]["ResultId"],
                    serialized_results[1]["ResultId"],
                ]
            },
        ),
    ],
)
def test_result_delete_data(mocker, cmd, expected_output):
    def get_result_side_effect(result_id):
        if result_id == serialized_results[0]["ResultId"]:
            return deepcopy(raw_results[0])
        elif result_id == serialized_results[1]["ResultId"]:
            return deepcopy(raw_results[1])
        raise ValueError(f"Unexpected result_id: {result_id}")

    # Create a mock channel that supports context manager
    mock_channel = Mock()
    mock_channel.__enter__ = Mock(return_value=mock_channel)
    mock_channel.__exit__ = Mock(return_value=None)

    # Patch the channel first
    mocker.patch("grpc.insecure_channel", return_value=mock_channel)

    # Patch the methods on ArmoniKResults class itself
    mocker.patch.object(ArmoniKResults, "get_result", side_effect=get_result_side_effect)
    mocker.patch.object(ArmoniKResults, "delete_result_data")

    # Run the command
    run_cmd_and_assert_exit_code(cmd)

    # Get the instance that was created during the test
    ArmonikResults_instance = ArmoniKResults.delete_result_data
    ArmonikResults_instance.assert_called_once_with(
        expected_output[serialized_results[0]["SessionId"]], serialized_results[0]["SessionId"]
    )


def test_result_create_file_not_found(mocker):
    # Create a mock channel that supports context manager
    mock_channel = Mock()
    mock_channel.__enter__ = Mock(return_value=mock_channel)
    mock_channel.__exit__ = Mock(return_value=None)

    # Patch the channel creation
    mocker.patch("grpc.insecure_channel", return_value=mock_channel)

    # Mock file operations to raise FileNotFoundError
    mocker.patch("builtins.open", side_effect=FileNotFoundError)

    # Run the command and expect it to fail
    run_cmd_and_assert_exit_code(
        [
            "result",
            "create",
            "my-session-id",
            "-r",
            "res file nonexistent",
            "--endpoint",
            ENDPOINT,
            "--debug",
        ],
        split=False,
        exit_code=2,
    )


def test_result_create_metadata_only(mocker):
    # Create a mock channel that supports context manager
    mock_channel = Mock()
    mock_channel.__enter__ = Mock(return_value=mock_channel)
    mock_channel.__exit__ = Mock(return_value=None)

    # Patch the channel creation
    mocker.patch("grpc.insecure_channel", return_value=mock_channel)

    # Patch the methods on ArmoniKResults class
    mocker.patch.object(ArmoniKResults, "create_results_metadata", return_value={})
    mocker.patch.object(ArmoniKResults, "create_results", return_value={})

    cmd = [
        "result",
        "create",
        "my-session-id",
        "--result",
        "result1",
        "--result",
        "result2",
        "--endpoint",
        ENDPOINT,
    ]
    run_cmd_and_assert_exit_code(cmd, split=False)

    ArmoniKResults.create_results_metadata.assert_called_once_with(
        session_id="my-session-id", result_names=["result1", "result2"]
    )
    ArmoniKResults.create_results.assert_not_called()


def test_result_create_with_bytes(mocker):
    # Create a mock channel that supports context manager
    mock_channel = Mock()
    mock_channel.__enter__ = Mock(return_value=mock_channel)
    mock_channel.__exit__ = Mock(return_value=None)

    # Patch the channel creation
    mocker.patch("grpc.insecure_channel", return_value=mock_channel)

    # Patch the methods on ArmoniKResults class
    mocker.patch.object(ArmoniKResults, "create_results_metadata", return_value={})
    mocker.patch.object(ArmoniKResults, "create_results", return_value={})

    cmd = [
        "result",
        "create",
        "my-session-id",
        "--result",
        "result1 bytes hello",
        "--result",
        "result2 bytes world",
        "--endpoint",
        ENDPOINT,
    ]
    run_cmd_and_assert_exit_code(cmd, split=False)

    ArmoniKResults.create_results_metadata.assert_not_called()
    ArmoniKResults.create_results.assert_called_once_with(
        session_id="my-session-id", results_data={"result1": b"hello", "result2": b"world"}
    )


def test_result_create_mixed(mocker):
    # Create a mock channel that supports context manager
    mock_channel = Mock()
    mock_channel.__enter__ = Mock(return_value=mock_channel)
    mock_channel.__exit__ = Mock(return_value=None)

    # Patch the channel creation
    mocker.patch("grpc.insecure_channel", return_value=mock_channel)

    # Patch the methods on ArmoniKResults class
    mocker.patch.object(ArmoniKResults, "create_results_metadata", return_value={})
    mocker.patch.object(ArmoniKResults, "create_results", return_value={})

    cmd = [
        "result",
        "create",
        "my-session-id",
        "--result",
        "result1",
        "--result",
        "result2 bytes hello",
        "--endpoint",
        ENDPOINT,
    ]
    run_cmd_and_assert_exit_code(cmd, split=False)

    ArmoniKResults.create_results_metadata.assert_called_once_with(
        session_id="my-session-id", result_names=["result1"]
    )
    ArmoniKResults.create_results.assert_called_once_with(
        session_id="my-session-id", results_data={"result2": b"hello"}
    )


def test_result_upload_data_from_bytes(mocker):
    # Create a mock channel that supports context manager
    mock_channel = Mock()
    mock_channel.__enter__ = Mock(return_value=mock_channel)
    mock_channel.__exit__ = Mock(return_value=None)

    # Patch the channel creation
    mocker.patch("grpc.insecure_channel", return_value=mock_channel)

    # Patch the methods on ArmoniKResults class
    mocker.patch.object(ArmoniKResults, "upload_result_data", return_value=None)

    cmd = [
        "result",
        "upload-data",
        "my-session-id",
        "result-id",
        "--from-bytes",
        "hello",
        "--endpoint",
        ENDPOINT,
    ]
    run_cmd_and_assert_exit_code(cmd, split=False)

    ArmoniKResults.upload_result_data.assert_called_once_with(
        "result-id", "my-session-id", b"hello"
    )


def test_result_upload_data_from_file(mocker):
    # Create a mock channel that supports context manager
    mock_channel = Mock()
    mock_channel.__enter__ = Mock(return_value=mock_channel)
    mock_channel.__exit__ = Mock(return_value=None)

    # Patch the channel creation
    mocker.patch("grpc.insecure_channel", return_value=mock_channel)

    # Patch the methods on ArmoniKResults class
    mocker.patch.object(ArmoniKResults, "upload_result_data", return_value=None)

    # Mock file operations
    mock_file_content = b"file content"
    mocker.patch("builtins.open", mock_open(read_data=mock_file_content))

    cmd = [
        "result",
        "upload-data",
        "my-session-id",
        "result-id",
        "--from-file",
        "test.txt",
        "--endpoint",
        ENDPOINT,
    ]
    run_cmd_and_assert_exit_code(cmd, split=False)

    ArmoniKResults.upload_result_data.assert_called_once_with(
        "result-id", "my-session-id", mock_file_content
    )


def test_result_upload_data_file_not_found(mocker):
    # Create a mock channel that supports context manager
    mock_channel = Mock()
    mock_channel.__enter__ = Mock(return_value=mock_channel)
    mock_channel.__exit__ = Mock(return_value=None)

    # Patch the channel creation
    mocker.patch("grpc.insecure_channel", return_value=mock_channel)

    # Mock file operations to raise FileNotFoundError
    mocker.patch("builtins.open", side_effect=FileNotFoundError)

    cmd = [
        "result",
        "upload-data",
        "my-session-id",
        "result-id",
        "--from-file",
        "nonexistent.txt",
        "--endpoint",
        ENDPOINT,
    ]
    run_cmd_and_assert_exit_code(cmd, split=False, exit_code=2)


def test_result_download_data(mocker):
    # Create a mock channel that supports context manager
    mock_channel = Mock()
    mock_channel.__enter__ = Mock(return_value=mock_channel)
    mock_channel.__exit__ = Mock(return_value=None)

    # Patch the channel creation
    mocker.patch("grpc.insecure_channel", return_value=mock_channel)

    # Patch the methods on ArmoniKResults class
    mocker.patch.object(ArmoniKResults, "download_result_data", return_value=raw_results[0])

    # Mock file operations
    mock_file_content = b"file content"
    mocker.patch("builtins.open", mock_open(read_data=mock_file_content))

    cmd = [
        "result",
        "download-data",
        "--endpoint",
        ENDPOINT,
        "session-id",
        "--id",
        "result-id",
        "--path",
        "output",
        "--suffix",
        "_session-id.txt",
        "--skip-not-found",
        "--debug",
    ]
    run_cmd_and_assert_exit_code(cmd, split=False)

    ArmoniKResults.download_result_data.assert_called_once_with("result-id", "session-id")
    open.assert_called_with(pathlib.PosixPath("output/result-id_session-id.txt"), "wb")

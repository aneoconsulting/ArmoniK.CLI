import json
import logging

from typing import Any, Dict, Optional, Union

from click.testing import CliRunner, Result
import pytest

from armonik_cli.cli import cli


def run_cmd_and_assert_exit_code(
    cmd: str,
    exit_code: int = 0,
    input: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    split: bool = True,
) -> Result:
    if split:
        cmd = cmd.split()
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, cmd, input=input, env=env)
        # Debugging: Print the result details
        print(f"Command: {cmd}")
        print(f"Result Output: {result.output}")
        print(f"Result Exit Code: {result.exit_code}")
        if result.exception:
            print(f"Exception: {result.exception}")
    assert result.exit_code == exit_code
    return result


def reformat_cmd_output(
    output: str, deserialize: bool = False, first_line_out: bool = False
) -> Union[str, Dict[str, Any]]:
    if first_line_out:
        output = "\n".join(output.split("\n")[1:])
    output = output.replace("\n", "")
    output = " ".join(output.split())
    if deserialize:
        return json.loads(output)
    return output


@pytest.fixture(autouse=True)
def disable_logging():
    """Disable all logging for tests."""
    logging.disable(logging.CRITICAL)  # This disables all logs below CRITICAL level
    yield
    logging.disable(logging.NOTSET)  # Re-enable logging after the test

import json

from typing import Dict, Optional

from click.testing import CliRunner, Result

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
) -> str:
    if first_line_out:
        output = "\n".join(output.split("\n")[1:])
    output = output.replace("\n", "")
    output = " ".join(output.split())
    if deserialize:
        return json.loads(output)
    return output

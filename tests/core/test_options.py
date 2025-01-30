import pytest
import rich_click as click

from click.testing import CliRunner

from armonik_cli.core.options import GlobalOption


@pytest.fixture(scope="module")
def cli_global_option():
    global_option_1 = click.option("--foo", type=str, cls=GlobalOption, default="value0")
    global_option_2 = click.option("--bar", type=str, cls=GlobalOption, required=True)

    @click.group()
    @global_option_1
    @global_option_2
    def cli(foo, bar):
        pass

    @cli.command()
    @global_option_1
    @global_option_2
    def command(foo, bar):
        click.echo(f"foo={foo}, bar={bar}")

    return cli


def test_global_option_at_group_level(cli_global_option):
    runner = CliRunner()
    result = runner.invoke(cli_global_option, ["--foo", "value1", "--bar", "value2", "command"])
    assert result.exit_code == 0
    assert result.output.strip() == "foo=value1, bar=value2"


def test_global_option_at_command_level(cli_global_option):
    runner = CliRunner()
    result = runner.invoke(cli_global_option, ["command", "--foo", "value1", "--bar", "value2"])
    assert result.exit_code == 0
    assert result.output.strip() == "foo=value1, bar=value2"


def test_global_option_at_group_and_command_level(cli_global_option):
    runner = CliRunner()
    result = runner.invoke(
        cli_global_option,
        ["--foo", "value1", "--bar", "value2", "command", "--foo", "value3", "--bar", "value4"],
    )
    assert result.exit_code == 0
    assert result.output.strip() == "foo=value3, bar=value4"


def test_global_option_default_value(cli_global_option):
    runner = CliRunner()
    result = runner.invoke(cli_global_option, ["--bar", "value2", "command"])
    assert result.exit_code == 0
    assert result.output.strip() == "foo=value0, bar=value2"


def test_global_option_required_missing(cli_global_option):
    runner = CliRunner()
    result = runner.invoke(cli_global_option, ["command"])
    assert result.exit_code == 2
    assert "Missing option" in result.output

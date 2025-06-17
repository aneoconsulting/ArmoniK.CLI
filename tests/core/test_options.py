import pytest
import rich_click as click

from click.testing import CliRunner
from armonik_cli_core.options import MutuallyExclusiveOption, GlobalOption


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


@pytest.fixture(scope="module")
def cli_mutually_exclusive_option():
    @click.command()
    @click.option("--foo", cls=MutuallyExclusiveOption, mutual=["bar"], help="Option foo.")
    @click.option("--bar", cls=MutuallyExclusiveOption, mutual=["foo"], help="Option bar.")
    def cli(foo, bar):
        click.echo(f"foo={foo}, bar={bar}")

    return cli


@pytest.fixture(scope="module")
def cli_mutually_exclusive_require_one_option():
    @click.command()
    @click.option(
        "--alpha",
        cls=MutuallyExclusiveOption,
        mutual=["beta"],
        require_one=True,
        help="Option alpha.",
    )
    @click.option(
        "--beta",
        cls=MutuallyExclusiveOption,
        mutual=["alpha"],
        require_one=True,
        help="Option beta.",
    )
    def cli_require_one(alpha, beta):
        click.echo(f"alpha={alpha}, beta={beta}")

    return cli_require_one


def test_mutual_exclusion(cli_mutually_exclusive_option):
    runner = CliRunner()
    result = runner.invoke(cli_mutually_exclusive_option, ["--foo", "value1", "--bar", "value2"])
    assert result.exit_code != 0
    assert "Illegal usage: `foo` cannot be used together with 'bar'" in result.output


def test_single_option_allowed(cli_mutually_exclusive_option):
    runner = CliRunner()
    result = runner.invoke(cli_mutually_exclusive_option, ["--foo", "value1"])
    assert result.exit_code == 0
    assert "foo=value1, bar=None" in result.output


def test_no_option_provided(cli_mutually_exclusive_option):
    runner = CliRunner()
    result = runner.invoke(cli_mutually_exclusive_option, [])
    assert result.exit_code == 0
    assert "foo=None, bar=None" in result.output


def test_require_one_missing(cli_mutually_exclusive_require_one_option):
    runner = CliRunner()
    result = runner.invoke(cli_mutually_exclusive_require_one_option, [])
    assert result.exit_code != 0
    assert "At least one of the following options must be provided: beta." in result.output


def test_require_one_provided(cli_mutually_exclusive_require_one_option):
    runner = CliRunner()
    result = runner.invoke(cli_mutually_exclusive_require_one_option, ["--alpha", "value1"])
    assert result.exit_code == 0
    assert "alpha=value1, beta=None" in result.output


def test_require_one_mutual_exclusion(cli_mutually_exclusive_require_one_option):
    runner = CliRunner()
    result = runner.invoke(
        cli_mutually_exclusive_require_one_option, ["--alpha", "value1", "--beta", "value2"]
    )
    assert result.exit_code != 0
    assert "Illegal usage: `alpha` cannot be used together with 'beta'" in result.output


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

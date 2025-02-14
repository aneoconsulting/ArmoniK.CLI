import rich_click as click

from rich.table import Table
from rich import print

from armonik_cli.core.config import CliConfig
from armonik_cli.core import base_group


@click.group(name="config")
@base_group
def config() -> None:
    """Manage CLI configuration."""
    pass


@config.command(name="get")
@click.argument(
    "field",
    type=click.Choice([field for field in CliConfig.ConfigModel.model_fields.keys()]),
    required=True,
)
def config_get(field: str) -> None:
    """Get the current CLI configuration."""
    click.echo(CliConfig().get(field))


@config.command(name="set")
@click.argument(
    "field",
    type=click.Choice([field for field in CliConfig.ConfigModel.model_fields.keys()]),
    required=True,
)
@click.argument("value", type=str, required=True)
def config_set(field: str, value: str) -> None:
    """Set a field in the CLI configuration."""
    CliConfig().set(**{field: value})
    click.echo(f"Set {field} to {value}")


@config.command(name="show")
def config_show():
    """Show the current CLI configuration."""
    config = CliConfig()
    for field, value in config._config.model_dump().items():
        click.echo(f"{field}: {value}")


@config.command(name="list")
def config_list():
    """List all available configuration fields."""
    available_commands_table = Table(title="Available configuration fields")
    available_commands_table.add_column("Field", justify="left")
    available_commands_table.add_column("Type", justify="left")
    available_commands_table.add_column("Default", justify="left")
    available_commands_table.add_column("Description", justify="left")
    for field_name, details in CliConfig.ConfigModel.model_fields.items():
        field_type, field_description = details.description.split(" - ")
        available_commands_table.add_row(
            field_name, field_type, str(details.default), field_description
        )
    print(available_commands_table)

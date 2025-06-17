import rich_click as click
from armonik_cli import commands, __version__

from armonik_cli_core import base_group
from armonik_cli_core.utils import populate_option_groups_incremental
from armonik_cli_core.groups import ENTRY_POINT_GROUP, ExtendableGroup, setup_command_groups

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"
click.rich_click.ERRORS_SUGGESTION = "Try running the '--help' flag for more information."
click.rich_click.ERRORS_EPILOGUE = (
    "To find out more, visit [link=https://github.com/aneoconsulting/ArmoniK.CLI]our repo[/link]."
)


@click.group(
    cls=ExtendableGroup,
    entry_point_group=ENTRY_POINT_GROUP,
    name="armonik",
    context_settings={"help_option_names": ["-h", "--help"], "auto_envvar_prefix": "AK"},
)
@click.version_option(version=__version__, prog_name="armonik")
@base_group
def cli(**kwargs) -> None:
    """
    ArmoniK CLI is a tool to monitor and manage ArmoniK clusters.
    """
    pass


cli.add_command(commands.extensions)
cli.add_command(commands.sessions)
cli.add_command(commands.tasks)
cli.add_command(commands.partitions)
cli.add_command(commands.results)
cli.add_command(commands.cluster)
cli.add_command(commands.config)

setup_command_groups()
populate_option_groups_incremental(cli)

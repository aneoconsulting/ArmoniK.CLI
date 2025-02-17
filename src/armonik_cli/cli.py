import rich_click as click

from typing import Dict, List, Union

from rich_click.utils import OptionGroupDict

from armonik_cli import commands, __version__
from armonik_cli.core import base_group


@click.group(name="armonik", context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="armonik")
@base_group
def cli() -> None:
    """
    ArmoniK CLI is a tool to monitor and manage ArmoniK clusters.
    """
    pass


cli.add_command(commands.sessions)
cli.add_command(commands.tasks)
cli.add_command(commands.partitions)
cli.add_command(commands.results)
cli.add_command(commands.cluster)


def get_command_paths_with_options(
    command: Union[click.Group, click.Command], parent: str = ""
) -> Dict[str, List[str]]:
    """
    Recursively retrieve all command paths and their associated options.

    Args:
        command: The root Click command or group.
        parent: The command path prefix for recursion.

    Returns:
        A dictionary where keys are command paths and values are
        strings listing their available options.
    """
    paths = {}

    full_path = f"{parent} {command.name}".strip()

    # Retrieve options as a string
    paths[full_path] = [
        max(opt.opts, key=len) for opt in command.params if isinstance(opt, click.Option)
    ]

    # Recurse if the command is a group
    if isinstance(command, click.Group):
        for subcommand in command.commands.values():
            paths.update(get_command_paths_with_options(subcommand, full_path))

    return paths


COMMON_OPTIONS_GROUP: OptionGroupDict = {
    "name": "Common options",
    "options": ["--debug", "--help", "--output"],
}

CLUSTER_CONFIG_OPTIONS_GROUP: OptionGroupDict = {
    "name": "Cluster config options",
    "options": ["--endpoint"],
}

click.rich_click.OPTION_GROUPS = {
    path: [
        COMMON_OPTIONS_GROUP,
        CLUSTER_CONFIG_OPTIONS_GROUP,
        {
            "name": "Command-specific options",
            "options": sorted(
                [
                    opt
                    for opt in options
                    if opt
                    not in COMMON_OPTIONS_GROUP["options"] + CLUSTER_CONFIG_OPTIONS_GROUP["options"]
                ]
            ),
        },
    ]
    for path, options in get_command_paths_with_options(cli).items()
}

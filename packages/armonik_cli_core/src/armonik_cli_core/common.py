import rich_click as click

from typing import Callable, Any, Dict, List, Union
from typing_extensions import TypeAlias
from .configuration import CliConfig

from rich_click.utils import OptionGroupDict


ClickOption: TypeAlias = Callable[[Callable[..., Any]], Callable[..., Any]]


def apply_click_params(
    command: Callable[..., Any], *click_options: ClickOption
) -> Callable[..., Any]:
    """
    Applies multiple Click options to a command.

    Args:
        command: The Click command function to decorate.
        *click_options: The Click options to apply.

    Returns:
        The decorated command function.
    """
    for click_option in click_options:
        command = click_option(command)
    return command


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


def populate_option_groups_incremental(
    command: Union[click.Group, click.Command], parent_path: str = ""
) -> None:
    """
    Populate option groups incrementally for a specific command tree.
    This adds to the existing OPTION_GROUPS rather than overwriting it.
    """
    COMMON_OPTIONS_GROUP: OptionGroupDict = {
        "name": "Common options",
        "options": ["--help", "--config", "--version"],
    }

    CLUSTER_CONFIG_OPTIONS_GROUP: OptionGroupDict = {
        "name": "Cluster connection options",
        "options": [],
    }

    # Build the common and cluster options from config fields
    for config_field_name, config_field_info in CliConfig.ConfigModel.model_fields.items():
        if (
            len(config_field_info.metadata) > 0
            and config_field_info.metadata[0].get("cli_option_group", "") == "Common"
        ):
            COMMON_OPTIONS_GROUP["options"].append(f"--{config_field_name.replace('_', '-')}")
        elif (
            len(config_field_info.metadata) > 0
            and config_field_info.metadata[0].get("cli_option_group", "") == "ClusterConnection"
        ):
            CLUSTER_CONFIG_OPTIONS_GROUP["options"].append(
                f"--{config_field_name.replace('_', '-')}"
            )

    # Get option paths for just this command tree
    paths_options = get_command_paths_with_options(command, parent_path)

    # Initialize OPTION_GROUPS if it doesn't exist
    if not hasattr(click.rich_click, "OPTION_GROUPS"):
        click.rich_click.OPTION_GROUPS = {}

    # Add option groups for each path in this command tree
    for path, options in paths_options.items():
        click.rich_click.OPTION_GROUPS[path] = [
            COMMON_OPTIONS_GROUP,
            CLUSTER_CONFIG_OPTIONS_GROUP,
            {
                "name": "Command-specific options",
                "options": sorted(
                    [
                        opt
                        for opt in options
                        if opt
                        not in COMMON_OPTIONS_GROUP["options"]
                        + CLUSTER_CONFIG_OPTIONS_GROUP["options"]
                    ]
                ),
            },
        ]

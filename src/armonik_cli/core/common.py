import rich_click as click

from typing import Callable, Any, get_origin
from typing_extensions import TypeAlias

from armonik_cli.core.config import CliConfig
from armonik_cli.core.options import GlobalOption


ClickOption: TypeAlias = Callable[[Callable[..., Any]], Callable[..., Any]]


endpoint_option = click.option(
    "-e",
    "--endpoint",
    type=str,
    required=True,
    help="Endpoint of the cluster to connect to.",
    metavar="ENDPOINT",
    cls=GlobalOption,
)


output_option = click.option(
    "-o",
    "--output",
    type=click.Choice(["yaml", "json", "table"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Commands output format.",
    metavar="FORMAT",
    cls=GlobalOption,
)


debug_option = click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Print debug logs and internal errors.",
    cls=GlobalOption,
)


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


def global_cluster_config_options(command: Callable[..., Any]) -> Callable[..., Any]:
    """
    Adds global configuration options to a Click command.

    Args:
        command: The Click command function to decorate.

    Returns:
        The decorated command function.
    """
    config = CliConfig()
    generated_click_options = []
    for field, field_info in CliConfig.ConfigModel.model_fields.items():
        generated_click_options.append(
            click.option(
                f"--{field.replace('_', '-')}",
                default=config.get(field),
                required=False,
                help=field_info.description.split(" - ")[1],
                cls=GlobalOption,
            )
        )
    return apply_click_params(command, *generated_click_options)
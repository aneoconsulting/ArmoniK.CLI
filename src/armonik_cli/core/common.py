from datetime import datetime
import time
import rich_click as click

from typing import Callable, Any
from typing_extensions import TypeAlias

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
    Adds global cluster configuration options to a Click command.

    Args:
        command: The Click command function to decorate.

    Returns:
        The decorated command function.
    """
    return apply_click_params(command, endpoint_option)


def global_common_options(command: Callable[..., Any]) -> Callable[..., Any]:
    """
    Adds global common options such as output format and debug mode to a Click command.

    Args:
        command: The Click command function to decorate.

    Returns:
        The decorated command function.
    """
    return apply_click_params(command, output_option, debug_option)


def format_timestamp(timestamp):
    """Format a timestamp as a human-readable string.

    Args:
        timestamp (Optional[float]): Unix timestamp to format. If None, returns "ongoing".

    Returns:
        str: Formatted time string in HH:MM:SS format, or "ongoing" if timestamp is None.
    """
    if timestamp is None:
        return "ongoing"
    return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")


def calculate_duration(start, end):
    """Calculate the duration between two timestamps.

    Args:
        start (float): The start time in seconds.
        end (Optional[float]): The end time in seconds. If None, the current time is used.

    Returns:
        float: Duration rounded to 2 decimal places.
    """
    if end is None:
        end = time.time()
    return round(end - start, 2)

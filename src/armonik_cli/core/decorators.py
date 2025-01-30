import grpc
import rich_click as click

from functools import wraps, partial
from typing import Callable, Optional, Any

from armonik_cli.core.console import console
from armonik_cli.core.common import global_cluster_config_options, global_common_options
from armonik_cli.exceptions import NotFoundError, InternalError, InternalArmoniKError


def error_handler(func: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
    """
    Decorator to handle errors for Click commands and ensure proper error display.

    Args:
        func: The command function to be decorated. If None, a partial function is returned,
            allowing the decorator to be used with parentheses.

    Returns:
        The wrapped function with error handling.
    """
    if func is None:
        return partial(error_handler)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except click.ClickException:
            raise
        except grpc.RpcError as err:
            status_code = err.code()
            error_details = f"{err.details()}."

            if status_code == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(error_details)
            elif status_code == grpc.StatusCode.INTERNAL:
                raise InternalArmoniKError(f"An internal exception has occurred:\n{error_details}")
            elif status_code == grpc.StatusCode.UNKNOWN:
                raise InternalArmoniKError(f"An unknown exception has occurred:\n{error_details}")
            else:
                raise InternalError("An internal fatal error occurred.")
        except Exception:
            if kwargs.get("debug", False):
                console.print_exception()
            else:
                raise InternalError("An internal fatal error occurred.")

    return wrapper


def base_group(func: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
    """
    Decorator to add global cluster configuration and common options to a Click group.

    Args:
        func: The Click group function to decorate. If None, a partial function is returned,
            allowing the decorator to be used with parentheses.

    Returns:
        The decorated Click group function.
    """
    if func is None:
        return partial(base_group)

    @global_cluster_config_options
    @global_common_options
    @wraps(func)
    def wrapper(endpoint: str, output: str, debug: bool, *args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper


def base_command(func: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
    """
    Decorator to add global cluster configuration and common options and error handling to a
    Click command function.

    Args:
        func: The command function to be decorated. If None, a partial function is returned,
            allowing the decorator to be used with parentheses.

    Returns:
        The wrapped function with added CLI options and error handling.
    """
    if func is None:
        return partial(base_command)

    @global_cluster_config_options
    @global_common_options
    @error_handler
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper

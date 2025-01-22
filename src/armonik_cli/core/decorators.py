import grpc

from functools import wraps, partial
from typing import Callable, Optional, Any

from armonik_cli.core.console import console
from armonik_cli.core.common import global_cluster_config_options, global_common_options
from armonik_cli.exceptions import (
    InternalCliError,
    InternalArmoniKError,
)


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
    def wrapper(*args, **kwargs):
        debug_mode = kwargs.get("debug", False)
        try:
            return func(*args, **kwargs)
        except grpc.RpcError as err:
            status_code = err.code()
            error_details = f"{err.details()} (gRPC Code: {status_code.name})."

            if debug_mode:
                console.print_exception()

            if status_code == grpc.StatusCode.INVALID_ARGUMENT:
                raise InternalCliError(error_details) from err
            elif status_code == grpc.StatusCode.NOT_FOUND:
                raise InternalArmoniKError(error_details) from err
            elif status_code == grpc.StatusCode.ALREADY_EXISTS:
                raise InternalArmoniKError(error_details) from err
            elif status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                raise InternalArmoniKError(error_details) from err
            elif status_code == grpc.StatusCode.INTERNAL:
                raise InternalArmoniKError(error_details) from err
            elif status_code == grpc.StatusCode.UNKNOWN:
                raise InternalArmoniKError(error_details) from err
            else:
                raise InternalArmoniKError(error_details) from err

        except Exception as e:
            if debug_mode:
                console.print_exception()
            raise InternalCliError(f"CLI errored with exception:\n{e}") from e

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

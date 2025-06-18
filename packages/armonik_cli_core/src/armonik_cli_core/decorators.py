import pathlib

import grpc
import rich_click as click

from functools import wraps, partial
from typing import Callable, List, Optional, Any, Tuple
from typing_extensions import TypeAlias

from .configuration import CliConfig
from .console import console

from .options import GlobalOption
from .logging import get_logger
from armonik_cli.exceptions import (
    InternalCliError,
    InternalArmoniKError,
)

from click.core import ParameterSource


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


def global_config_options(command: Callable[..., Any]) -> Callable[..., Any]:
    generated_click_options = [
        click.option(
            "-c",
            "--config",
            "additional_config",
            type=click.Path(exists=True, dir_okay=False),
            required=False,
            help="Path to additional config file.",
            envvar="AKCONFIG",
            cls=GlobalOption,
        )
    ]
    for _, field_info in CliConfig.ConfigModel.model_fields.items():
        if (
            len(field_info.metadata) > 0
            and "cli_option" in field_info.metadata[0]
            and field_info.metadata[0]["cli_option"]
        ):
            generated_click_options.append(field_info.metadata[0]["cli_option"])
    return apply_click_params(command, *generated_click_options)


def inject_config(func: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
    """
    Decorator to inject a CLI configuration object into a Click command.

    Args:
        func: The command function to be decorated. If None, a partial function is returned,
            allowing the decorator to be used with parentheses.

    Returns:
        The wrapped function with the CLI configuration object injected.
    """
    if func is None:
        return partial(inject_config)

    @click.pass_context
    @wraps(func)
    def wrapper(ctx, *args, **kwargs):
        def filter_defaults(x: dict) -> dict:
            """Remove non-explicitly assigned values from the incoming commandline config."""
            return {
                key: value
                for key, value in x.items()
                if ctx.get_parameter_source(key)
                not in [ParameterSource.DEFAULT, ParameterSource.DEFAULT_MAP]
                or key in ctx.obj
            }

        final_config = CliConfig()
        if "additional_config" in kwargs and kwargs["additional_config"] is not None:
            additional_config = CliConfig.from_file(pathlib.Path(kwargs["additional_config"]))
            final_config = final_config.layer(**additional_config.model_dump(exclude_unset=True))
            final_config = final_config.layer(**filter_defaults(kwargs))
        else:
            final_config = final_config.layer(**filter_defaults(kwargs))
        final_config.validate_config()
        kwargs["config"] = final_config
        return func(*args, **kwargs)

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

    @global_config_options
    @click.pass_context
    @wraps(func)
    def wrapper(ctx, *args: Any, **kwargs: Any) -> Any:
        if not isinstance(ctx.obj, list):
            ctx.obj = []
        for param in kwargs.keys():
            if ctx.get_parameter_source(param) not in [
                ParameterSource.DEFAULT or ParameterSource.DEFAULT_MAP
            ]:
                ctx.obj.append(param)
        return func(*args, **kwargs)

    return wrapper


def base_command(
    func: Optional[Callable[..., Any]] = None,
    *,
    pass_config: bool = False,
    auto_output: Optional[str] = None,
    default_table: Optional[List[Tuple[str, str]]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to add global cluster configuration, common options, and error handling
    to a Click command function.

    Args:
        func (Optional[Callable]): The function to be decorated. If None, returns a decorator.
        pass_config (bool): If True, passes the config to the decorated function.
        auto_output (Optional[str]): If provided, overrides 'auto' output format with this value.

    Returns:
        Callable: A decorator that wraps the function with CLI options and error handling.
    """
    if func is None:
        return partial(
            base_command,
            pass_config=pass_config,
            auto_output=auto_output,
            default_table=default_table,
        )

    @error_handler
    @inject_config
    @global_config_options
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if auto_output is not None and kwargs.get("output") == "auto":
            kwargs["config"].output = auto_output
            kwargs["output"] = auto_output
        if not pass_config:
            kwargs.pop("config", None)
            kwargs.pop("additional_config", None)
            kwargs["logger"] = get_logger("armonik_cli", debug=False, verbose=False)
        else:
            kwargs["logger"] = get_logger(
                "armonik_cli", debug=kwargs["config"].debug, verbose=kwargs["config"].verbose
            )
        kwargs["logger"].debug(f"Executing command: {func.__name__}")
        kwargs["logger"].debug(f"Config: {kwargs.get('config', None)}")
        kwargs["logger"].debug(f"Arguments: {kwargs}")
        command_out = func(*args, **kwargs)
        if command_out:
            command_group, command_name, *_ = func.__name__.split("_", 2)
            console.formatted_print(
                command_out,
                print_format=kwargs["config"].output,
                table_cols=table_cols
                if (table_cols := kwargs["config"].get_table_columns(command_group, command_name))
                else default_table,
            )

    return wrapper

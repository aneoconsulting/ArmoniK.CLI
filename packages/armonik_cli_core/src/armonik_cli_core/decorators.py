import pathlib

from armonik_cli_core.configuration_v2 import CliConfigSchema
import grpc
import rich_click as click

from functools import wraps, partial
from typing import Callable, List, Optional, Any, Tuple, Type, TypeVar, Union, cast, TYPE_CHECKING
from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from armonik_cli_core.groups import EnrichedGroup

from .configuration import CliConfig
from .console import console

from .options import GlobalOption
from .logging import get_logger
from armonik_cli_core.exceptions import (
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


# TODO: It shouldn't be manual
def global_config_options(command: Callable[..., Any]) -> Callable[..., Any]:
    """Register all global CLI options (--endpoint, --output, etc.) on a command."""
    return apply_click_params(
        command,
        click.option(
            "-c", "--config", "additional_config",
            type=click.Path(exists=True, dir_okay=False),
            required=False,
            help="Path to additional config file.",
            envvar="AKCONFIG",
            cls=GlobalOption,
        ),
        click.option(
            "-e", "--endpoint", "endpoint",
            type=str, default=None, required=False,
            help="ArmoniK cluster endpoint URL.",
            envvar="AK__Endpoint",
            cls=GlobalOption,
        ),
        click.option(
            "--ca", "--certificate-authority", "certificate_authority",
            type=click.Path(exists=True, dir_okay=False),
            default=None, required=False,
            help="Path to CA certificate.",
            envvar="AK__CertificateAuthority",
            cls=GlobalOption,
        ),
        click.option(
            "--client-cert", "client_certificate",
            type=click.Path(exists=True, dir_okay=False),
            default=None, required=False,
            help="Path to client certificate.",
            envvar="AK__ClientCertificate",
            cls=GlobalOption,
        ),
        click.option(
            "--client-key", "client_key",
            type=click.Path(exists=True, dir_okay=False),
            default=None, required=False,
            help="Path to client key.",
            envvar="AK__ClientKey",
            cls=GlobalOption,
        ),
        click.option(
            "-o", "--output", "output",
            type=click.Choice(["json", "yaml", "table", "auto"]),
            default="auto", required=False,
            help="Output format.",
            cls=GlobalOption,
        ),
        click.option(
            "-d", "--debug", "debug",
            is_flag=True, default=False,
            help="Enable debug mode.",
            cls=GlobalOption,
        ),
        click.option(
            "-v", "--verbose", "verbose",
            is_flag=True, default=False,
            help="Enable verbose output.",
            cls=GlobalOption,
        ),
    )
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
    func=None,
    *,
    requires=None,
    auto_output=None,
    default_table=None,
):
    """
    New-style command decorator that uses build_config() instead of inject_config.

    Commands using this decorator declare what config categories they need.
    If requires is None or empty, no config object is injected at all.
    """
    if func is None:
        return partial(
            base_command,
            requires=requires,
            auto_output=auto_output,
            default_table=default_table,
        )

    @error_handler
    @global_config_options
    @click.pass_context
    @wraps(func)
    def wrapper(ctx, *args, **kwargs):
        needs_config = requires is not None and len(requires) > 0
        print(f"DEBUG layered_command: requires={requires}, needs_config={needs_config}")

        # Names of kwargs that come from global_config_options
        config_kwarg_names = {
            "endpoint", "certificate_authority", "client_certificate",
            "client_key", "output", "debug", "verbose", "additional_config",
        }

        if needs_config:
            from .configuration_v2 import build_config

            # Extract config-related kwargs
            config_kwargs = {}
            for k in list(kwargs):
                if k in config_kwarg_names:
                    val = kwargs.pop(k)
                    source = ctx.get_parameter_source(k)
                    if source not in (ParameterSource.DEFAULT, ParameterSource.DEFAULT_MAP):
                        config_kwargs[k] = val

            additional_config = config_kwargs.pop("additional_config", None)

            config = build_config(
                cli_kwargs=config_kwargs,
                additional_config_path=additional_config,
                requires=requires,
            )
            kwargs["config"] = config

            # Resolve output
            if auto_output and config.output == "auto":
                config._schema.output = auto_output
            kwargs["output"] = config.output

            # Logger from config
            kwargs["logger"] = get_logger(
                "armonik_cli", debug=config.debug, verbose=config.verbose
            )
        else:
            # Strip all config kwargs — command doesn't want them
            output = kwargs.pop("output", "auto")
            debug = kwargs.pop("debug", False)
            verbose = kwargs.pop("verbose", False)
            for k in list(kwargs):
                if k in config_kwarg_names:
                    kwargs.pop(k)

            if auto_output:
                output = auto_output
            kwargs["output"] = output
            kwargs["logger"] = get_logger("armonik_cli", debug=debug, verbose=verbose)

        # Execute
        kwargs["logger"].debug(f"Executing command: {func.__name__}")
        command_out = func(*args, **kwargs)

        # Auto-print
        if command_out and needs_config:
            command_group, command_name, *_ = func.__name__.split("_", 2)
            config = kwargs["config"]
            console.formatted_print(
                command_out,
                print_format=config.output,
                table_cols=config.get_table_columns(command_group, command_name)
                    or default_table,
            )

        return command_out

    return wrapper



_AnyCallable = Callable[..., Any]
GrpType = TypeVar("GrpType", bound=click.RichGroup)
CmdType = TypeVar("CmdType", bound=click.RichCommand)


def armonik_cli_core_command(
    name: Union[str, _AnyCallable, None] = None,
    group: Optional[click.RichGroup] = None,
    cls: Optional[Type[CmdType]] = None,
    use_global_options: bool = True,
    pass_config: bool = False,
    auto_output: Optional[str] = None,
    default_table: Optional[List[Tuple[str, str]]] = None,
    requires=None,
    **attrs: Any,
) -> Union[click.Command, Callable[[_AnyCallable], Union[click.Command, CmdType]]]:
    """
    Custom command decorator function to :
    - Handle ArmoniK CLI specific options
    - Automatically applying global options.

    Args:
        name: Name of the command
        group: Group to add the command to
        cls: Custom command class to use
        use_global_options: Whether to use global options or not
        pass_config: If True, passes the config to the decorated function
        auto_output: If provided, overrides 'auto' output format with this value
        default_table: Default table columns for output formatting
        requires: Required validation groups to engage
        **attrs: All other parameters passed to rich_click.command
    """

    # Handle the normal case where decorator is used with parentheses
    # e.g., @armonik_cli_core_command(name="process") or @armonik_cli_core_command()
    def decorator(func):
        # Apply base_command first if needed, then rich_click.command
        if use_global_options:
            func = base_command(
                func,
                requires=requires,
                auto_output=auto_output,
                default_table=default_table,
            )

        if group:
            command_instance = group.command(name, cls=group.command_class, **attrs)(func)
        else:
            command_instance = click.command(name=name, cls=cls, **attrs)(func)
        return command_instance

    return decorator


def armonik_cli_core_group(
    name: Union[str, _AnyCallable, None] = None,
    cls: Optional[Type[GrpType]] = None,
    use_global_options: bool = True,
    use_custom_parsing: bool = True,
    **attrs: Any,
) -> Union[click.Group, Callable[[_AnyCallable], Union["EnrichedGroup", GrpType]]]:
    """
    Custom group decorator function that creates an EnrichedGroup (similar to click's group decorator).

    Args:
        name: Name of the group
        cls: Custom group class to use
        use_global_options: Whether to apply base_group decorator
        use_custom_parsing: Whether to use EnrichedGroup as default cls
        **attrs: All other parameters passed to click.group
    """
    # Set default cls if not provided and use_custom_parsing is True
    if cls is None and use_custom_parsing:
        from armonik_cli_core.groups import EnrichedGroup

        cls = cast(Type[GrpType], EnrichedGroup)

    # Handle the normal case where decorator is used with parentheses
    # e.g., @armonik_cli_core_group(name="sessions") or @armonik_cli_core_group()
    def decorator(func):
        # Apply base_group first if needed, then click.group
        if use_global_options:
            func = base_group(func)

        group_instance = click.group(name=name, cls=cls, **attrs)(func)
        return group_instance

    return decorator

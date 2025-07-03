from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar, Union
import rich_click as click

from .decorators import base_command

_AnyCallable = Callable[..., Any]
CmdType = TypeVar("CmdType", bound=click.Command)


class AkCommand(click.Command):
    def parse_args(self, ctx, args):
        # Store the original required state of the parameters
        original_required = {param: param.required for param in self.params}

        try:
            # Temporarily mark all parameters as not required
            for param in self.params:
                param.required = False

            # Let the parent class parse the arguments
            # This will populate ctx.params without raising MissingParameter errors
            super().parse_args(ctx, args)

            # Custom validation logic for multiple missing parameters
            missing_params = []
            for param in self.get_params(ctx):
                # Check if the parameter was originally required and is now missing
                if original_required.get(param) and ctx.params.get(param.name) is None:
                    missing_params.append(param)

            if missing_params:
                # Get the error hints for all missing parameters
                param_hints = [param.get_error_hint(ctx) for param in missing_params]

                if len(missing_params) > 1:
                    error_msg = f"Missing required options: {', '.join(param_hints)}"
                else:
                    error_msg = f"Missing required option: {param_hints[0]}"

                # Use UsageError for better formatting of this type of error
                raise click.UsageError(error_msg, ctx=ctx)

        finally:
            # --- IMPORTANT: Restore the original 'required' state ---
            for param in self.params:
                param.required = original_required.get(param, False)


def ak_command(
    name: Union[str, _AnyCallable, None] = None,
    group: Optional[click.Group] = None,
    cls: Optional[Type[CmdType]] = None,
    use_global_options: bool = True,
    pass_config: bool = False,
    auto_output: Optional[str] = None,
    default_table: Optional[List[Tuple[str, str]]] = None,
    **attrs: Any,
) -> Union[click.Command, Callable[[_AnyCallable], Union[click.Command, CmdType]]]:
    """
    Custom command decorator function.

    Args:
    Group:
        name: Name of the command
        group: Group to add the command to
        cls: Custom command class to use
        use_global_options: Whether to apply base_command decorator
        pass_config: If True, passes the config to the decorated function (base_command arg)
        auto_output: If provided, overrides 'auto' output format with this value (base_command arg)
        default_table: Default table columns for output formatting (base_command arg)
        **attrs: All other parameters passed to rich_click.command
    """

    # Handle the case where the decorator is used without parentheses
    # e.g., @ak_command instead of @ak_command()
    if callable(name):
        func = name

        # Apply base_command first if needed, then rich_click.command
        if use_global_options:
            func = base_command(
                func,
                pass_config=pass_config,
                auto_output=auto_output,
                default_table=default_table,
            )
        if group:
            command_instance = group.command(cls=cls, **attrs)(func)
        else:
            command_instance = click.command(cls=cls, **attrs)(func)
        return command_instance

    # Handle the normal case where decorator is used with parentheses
    # e.g., @ak_command(name="process") or @ak_command()
    def decorator(func):
        # Apply base_command first if needed, then rich_click.command
        if use_global_options:
            func = base_command(
                func,
                pass_config=pass_config,
                auto_output=auto_output,
                default_table=default_table,
            )

        if group:
            command_instance = group.command(name, cls=cls, **attrs)(func)
        else:
            command_instance = click.command(name, cls=cls, **attrs)(func)
        return command_instance

    return decorator

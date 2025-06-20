import rich_click as click

from typing import Any, List, Tuple, Mapping


class GlobalOption(click.Option):
    """
    A custom Click option that allows the option to be passed anywhere in the command path.

    This class extends the standard Click Option to enable the option to be recognized
    and processed regardless of its position in the command hierarchy.
    """

    def __init__(self, *args, **kwargs):
        self.globally_required = kwargs.pop("required", False)
        super().__init__(*args, **kwargs, required=False)

    def process_value(self, ctx: click.Context, value: Any) -> Any:
        """
        Process the value of the option.

        This method overrides the default behavior to check if the option's value
        is not provided in the current context but is available in the parent context.

        So, if all the command groups in a command path have the same option using this
        class, then successive evaluation of the process_value method will forward the
        value of the option wherever it is provided in the command hierarchy.

        Args:
            ctx: The current context in which the option is being processed.
            value: The value of the option provided in the current context.

        Returns:
            The processed value of the option.
        """
        value = super().process_value(ctx, value)
        # If the option is not passed at this level of the command hierarchy, try to retrieve it from
        # the parent command, if one exists.
        if (not value or value == self.default) and ctx.parent and self.name in ctx.parent.params:
            value = ctx.parent.params[self.name]
        # Raise an exception if the option is required and has not been passed at any level of the
        # command hierarchy.
        if not value and not isinstance(ctx.command, click.Group) and self.globally_required:
            raise click.MissingParameter(ctx=ctx)
        return value


class MutuallyExclusiveOption(click.Option):
    """
    A custom Click option class that enforces mutual exclusivity between specified options
    and optionally requires at least one of the mutual options to be passed.

    Attributes:
        mutual: A list of option names that cannot be used together with this option.
        require_one: Whether at least one of the mutually exclusive options must be provided.
    """

    def __init__(self, *args, **kwargs):
        self.mutual = set(kwargs.pop("mutual", []))
        self.require_one = kwargs.pop("require_one", False)

        if self.mutual:
            mutual_text = f" This option cannot be used together with {' or '.join(self.mutual)}."
            kwargs["help"] = f"{kwargs.get('help', '')}{mutual_text}"

        if self.require_one:
            kwargs["help"] = (
                f"{kwargs.get('help', '')} At least one of these options must be provided."
            )

        super().__init__(*args, **kwargs)

    def handle_parse_result(
        self, ctx: click.Context, opts: Mapping[str, Any], args: List[str]
    ) -> Tuple[Any, List[str]]:
        """
        Handle the parsing of command-line options, enforcing mutual exclusivity
        and the requirement of at least one mutual option if specified.

        Args:
            ctx: The Click context.
            opts: A dictionary of the parsed command-line options.
            args: The remaining command-line arguments.

        Returns:
            The result of the superclass's `handle_parse_result` method.

        Raises:
            click.UsageError: If mutual exclusivity is violated or if none of the required options are provided.
        """
        mutex = self.mutual.intersection(opts)

        # Enforce mutual exclusivity
        if mutex and self.name in opts:
            raise click.UsageError(
                f"Illegal usage: `{self.name}` cannot be used together with '{', '.join(mutex)}'."
            )

        # Enforce that at least one mutual option is provided
        if self.require_one and not mutex and self.name not in opts:
            raise click.UsageError(
                f"At least one of the following options must be provided: {', '.join(self.mutual)}."
            )

        return super().handle_parse_result(ctx, opts, args)

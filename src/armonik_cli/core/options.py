import rich_click as click

from typing import Any


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

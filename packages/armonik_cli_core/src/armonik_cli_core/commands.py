from typing import List
from click import Context
import rich_click as click


class EnrichedCommand(click.Command):
    """Enhanced Click command with improved error handling for missing required parameters.

    This class extends rich_click.Command to provide better error messages when multiple
    required parameters are missing. Instead of stopping at the first missing parameter,
    it collects all missing required parameters and displays them together in a single
    error message.

    The class temporarily disables the 'required' flag on all parameters during parsing
    to prevent early termination, then performs custom validation to identify all missing
    required parameters at once.

    Example:
        Instead of showing:
            "Error: Missing option '--param1'"

        When multiple parameters are missing, it shows:
            "Error: Missing required options: --param1, --param2, --param3"

    Attributes:
        Inherits all attributes from rich_click.Command.

    Methods:
        parse_args(ctx, args): Override of parent method with enhanced error handling.
    """

    def parse_args(self, ctx: Context, args: List[str]):
        """Parse command-line arguments with enhanced missing parameter error handling.

        This method temporarily disables the 'required' flag on all parameters to allow
        complete parsing, then performs custom validation to identify all missing required
        parameters and display them in a single, comprehensive error message.

        Args:
            ctx (click.Context): The Click context object containing command state.
            args (list): List of command-line arguments to parse.

        Raises:
            click.UsageError: When one or more required parameters are missing, with
                             a message listing all missing parameters.

        Note:
            The original 'required' state of all parameters is preserved and restored
            after parsing, ensuring the command object remains in its original state
            regardless of whether parsing succeeds or fails.
        """
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
                if (
                    original_required.get(param)
                    and param.name
                    and ctx.params.get(param.name) is None
                ):
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

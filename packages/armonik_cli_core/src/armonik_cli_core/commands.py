import rich_click as click


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

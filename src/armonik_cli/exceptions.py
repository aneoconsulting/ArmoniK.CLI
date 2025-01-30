import rich_click as click
from rich.panel import Panel
from rich import print


class ArmoniKCLIError(click.ClickException):
    """Base exception for ArmoniK CLI errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

    def show(self, file=None):
        """Override to display errors in a cleaner format."""
        print(Panel(self.format_message(), title="Error", style="red"))


class InternalCliError(ArmoniKCLIError):
    """Error raised when an unknown internal error occured."""

    exit_code = 3


class InternalArmoniKError(ArmoniKCLIError):
    """Error raised when there's an error in ArmoniK, you need to check the logs there for more information."""

    exit_code = 4

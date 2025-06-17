import rich_click as click

from rich.traceback import Traceback
from .console import console

from importlib.metadata import entry_points


ENTRY_POINT_GROUP = "armonik.cli.extensions"


class BrokenExtension(click.RichCommand):
    """
    A Click command that represents a broken or failed-to-load extension.

    When an extension fails to load due to import errors or other issues,
    this command is used as a placeholder that displays the error details
    when invoked by the user.
    """

    def __init__(self, name, error):
        """
        Initialize a broken extension command.

        Args:
            name (str): The name of the broken extension
            error (Exception): The exception that occurred while loading the extension
        """
        super().__init__(name, help=f"Error: Failed to load extension '{name}'.")
        self.error = error
        self.extension_name = name

    def invoke(self, ctx):
        """
        When invoked, print the error details and raise a ClickException.

        Args:
            ctx: Click context object

        Raises:
            click.ClickException: Always raised after displaying error details
        """
        console.print(
            f"Error: The extension '{self.name}' is broken and could not be loaded.",
            fg="red",
            err=True,
        )
        console.print("The following error was caught:", fg="yellow", err=True)
        try:
            raise self.error
        except Exception:
            traceback_obj = Traceback(show_locals=True, word_wrap=True, extra_lines=2)
            console.print(traceback_obj)

            raise click.ClickException(f"Extension '{self.name}' broken.")


class ExtendableGroup(click.RichGroup):
    """
    A Click group that can be extended with commands loaded from entry points.

    This class extends the standard Click group functionality to dynamically
    discover and load commands from Python entry points, allowing for a
    plugin-based architecture where extensions can add new commands to the CLI.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the extendable group.

        Args:
            *args: Positional arguments passed to the parent RichGroup
            **kwargs: Keyword arguments passed to the parent RichGroup.
                     'entry_point_group' is extracted and used for extension discovery.
        """
        self.entry_point_group = kwargs.pop("entry_point_group", None)
        self._loaded_commands = set()
        self._extension_commands = None  # Cache extension command names
        super().__init__(*args, **kwargs)

    def _get_extension_command_names(self):
        """
        Get list of extension command names (cached).

        Discovers available extension commands from entry points and caches
        the result to avoid repeated discovery operations.

        Returns:
            list: List of extension command names
        """
        if self._extension_commands is not None:
            return self._extension_commands

        if not self.entry_point_group:
            self._extension_commands = []
            return self._extension_commands

        try:
            discovered_eps = entry_points(group=self.entry_point_group)
            self._extension_commands = [ep.name for ep in discovered_eps]
        except Exception:
            self._extension_commands = []

        return self._extension_commands

    def list_commands(self, ctx):
        """
        Lists command names by combining statically defined commands
        with dynamically discovered extension commands from entry points.

        Args:
            ctx: Click context object

        Returns:
            list: Sorted list of all available command names
        """
        static_commands = super().list_commands(ctx)

        extension_commands = self._get_extension_command_names()

        self._update_command_groups(static_commands, extension_commands)

        return sorted(list(set(static_commands + extension_commands)))

    def _update_command_groups(self, static_commands, extension_commands):
        """
        Update rich-click command groups for better CLI help display.

        Organizes commands into groups (Core Commands and Extensions) for
        improved help text formatting with rich-click.

        Args:
            static_commands (list): List of statically defined command names
            extension_commands (list): List of extension command names
        """
        if not static_commands and not extension_commands:
            return

        # Determine the group name (this will be the CLI name or empty string)
        group_name = self.name or "cli"

        # Build command groups
        command_groups = []

        if static_commands:
            command_groups.append(
                {
                    "name": "Core Commands",
                    "commands": static_commands,
                }
            )

        if extension_commands:
            command_groups.append(
                {
                    "name": "Extensions",
                    "commands": extension_commands,
                }
            )

        # Set the command groups for this CLI
        click.rich_click.COMMAND_GROUPS[group_name] = command_groups

    def get_command(self, ctx, cmd_name):
        """
        Override to populate option groups when commands are accessed.

        First checks for built-in commands, then looks for extension commands
        from entry points. If an extension fails to load, returns a BrokenExtension
        command that displays the error when invoked.

        Args:
            ctx: Click context object
            cmd_name (str): Name of the command to retrieve

        Returns:
            click.Command or None: The command object if found, None otherwise
        """
        # First, check for a built-in command
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            self._ensure_option_groups_populated(command, cmd_name)
            return command

        # If no built-in command is found, look for an extension
        if not self.entry_point_group:
            return None

        discovered_eps = entry_points(group=self.entry_point_group)
        ep = next((ep for ep in discovered_eps if ep.name == cmd_name), None)

        if ep is None:
            return None

        try:
            loaded_extension = ep.load()

            if isinstance(loaded_extension, (click.Command, click.Group)):
                self._ensure_option_groups_populated(loaded_extension, cmd_name)
                return loaded_extension
            else:
                raise TypeError(f"Extension '{cmd_name}' did not load a Click Command or Group.")

        except Exception as e:
            return BrokenExtension(name=cmd_name, error=e)

    def _ensure_option_groups_populated(self, command, cmd_name):
        """
        Ensure option groups are populated for a command.

        Populates option groups for better help display formatting,
        tracking which commands have already been processed to avoid
        duplicate work.

        Args:
            command (click.Command): The command to populate option groups for
            cmd_name (str): Name of the command
        """
        command_key = f"{self.name}-{cmd_name}" if self.name else cmd_name

        if command_key not in self._loaded_commands:
            self._loaded_commands.add(command_key)

            parent_path = self.name if self.name else ""

            from armonik_cli_core.utils import populate_option_groups_incremental

            populate_option_groups_incremental(command, parent_path)


def setup_command_groups():
    """
    Set up command groups for the main CLI.

    Configures the rich-click command groups to organize core commands
    and extension commands into separate sections for better help display.
    This function should be called during CLI initialization to ensure
    proper command grouping in help text.
    """
    core_commands = ["extension", "session", "task", "partition", "result", "cluster", "config"]

    # Get extension commands
    extension_commands = []
    try:
        discovered_eps = entry_points(group=ENTRY_POINT_GROUP)
        extension_commands = [ep.name for ep in discovered_eps]
    except Exception:
        pass

    # Set up command groups
    command_groups = [
        {
            "name": "Core Commands",
            "commands": core_commands,
        }
    ]

    if extension_commands:
        command_groups.append(
            {
                "name": "Extensions",
                "commands": extension_commands,
            }
        )

    click.rich_click.COMMAND_GROUPS = {"armonik": command_groups}

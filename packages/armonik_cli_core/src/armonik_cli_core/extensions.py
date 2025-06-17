import rich_click as click

from rich.traceback import Traceback
from rich.console import Console
from rich.text import Text

from importlib.metadata import entry_points


ENTRY_POINT_GROUP = "armonik.cli.extensions"

class BrokenExtension(click.RichCommand):
    def __init__(self, name, error):
        super().__init__(name, help=f"[red]Error: Failed to load extension '{name}'.[/]")
        self.error = error
        self.extension_name = name

    def invoke(self, ctx):
        """When invoked, print the error details."""
        click.secho(f"Error: The extension '{self.name}' is broken and could not be loaded.", fg="red", err=True)
        click.secho("The following error was caught:", fg="yellow", err=True)
        console = Console(stderr=True)
        try:
            raise self.error
        except Exception:
            traceback_obj = Traceback(
                show_locals=True, 
                word_wrap=True,
                extra_lines=2
            )
            console.print(traceback_obj)
        
            raise click.ClickException(f"Extension '{self.name}' broken.")



class ExtendableGroup(click.RichGroup):
    def __init__(self, *args, **kwargs):
        self.entry_point_group = kwargs.pop("entry_point_group", None)
        self._loaded_commands = set()
        self._extension_commands = None  # Cache extension command names
        super().__init__(*args, **kwargs)
        

    def _get_extension_command_names(self):
        """Get list of extension command names (cached)."""
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
        """
        # Get static commands
        static_commands = super().list_commands(ctx)
        
        # Get extension commands
        extension_commands = self._get_extension_command_names()
        
        # Update command groups for rich-click
        self._update_command_groups(static_commands, extension_commands)
        
        # Combine and return all commands
        return sorted(list(set(static_commands + extension_commands)))

    def _update_command_groups(self, static_commands, extension_commands):
        """Update rich-click command groups."""
        if not static_commands and not extension_commands:
            return
            
        # Determine the group name (this will be the CLI name or empty string)
        group_name = self.name or "cli"
        
        # Build command groups
        command_groups = []
        
        if static_commands:
            command_groups.append({
                "name": "Core Commands",
                "commands": static_commands,
            })
        
        if extension_commands:
            command_groups.append({
                "name": "Extensions",
                "commands": extension_commands,
            })
        
        # Set the command groups for this CLI
        click.rich_click.COMMAND_GROUPS[group_name] = command_groups

    def get_command(self, ctx, cmd_name):
        """Override to populate option groups when commands are accessed."""
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
        """Ensure option groups are populated for a command."""
        command_key = f"{self.name}-{cmd_name}" if self.name else cmd_name
        
        if command_key not in self._loaded_commands:
            self._loaded_commands.add(command_key)
            
            parent_path = self.name if self.name else ""
            
            from armonik_cli_core.common import populate_option_groups_incremental
            populate_option_groups_incremental(command, parent_path)


def setup_command_groups():
    """Set up command groups for the main CLI."""
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
        command_groups.append({
            "name": "Extensions",
            "commands": extension_commands,
        })
    
    click.rich_click.COMMAND_GROUPS = {
        "armonik": command_groups
    }

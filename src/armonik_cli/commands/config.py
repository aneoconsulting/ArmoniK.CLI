import armonik_cli_core as akcc

from rich.table import Table
from rich.syntax import Syntax
from rich.console import Group
from rich.panel import Panel

from armonik_cli_core.configuration_v2 import CliConfig, CliConfigSchema

akcc.rich_click.USE_RICH_MARKUP = True
akcc.rich_click.USE_MARKDOWN = True


@akcc.group(name="config")
def config(**kwargs) -> None:
    """Manage CLI configuration."""
    pass


@config.command(name="get", requires=["common"])
@akcc.argument("field", type=str, required=True)
def config_get(field: str, **kwargs) -> None:
    """Get the current CLI configuration."""
    schema_fields = CliConfigSchema._field_defs
    if field in schema_fields:
        c = CliConfig()
        akcc.console.print(c.get(field))
    else:
        raise akcc.ClickException(
            f"Field '{field}' is not part of the configuration. "
            f"Available fields: {', '.join(schema_fields.keys())}"
        )


@config.command(name="set", requires=[""])
@akcc.argument("field", type=str, required=True)
@akcc.argument("value", type=str, required=True)
def config_set(field: str, value: str, **kwargs) -> None:
    """Set a field in the CLI configuration."""
    schema_fields = CliConfigSchema._field_defs
    if field in schema_fields:
        c = CliConfig()
        c.set(**{field: value})
        akcc.console.print(f"Set {field} to {value}")
    else:
        raise akcc.ClickException(
            f"Field '{field}' is not part of the configuration. "
            f"Available fields: {', '.join(schema_fields.keys())}"
        )


@config.command(name="show", requires=[])
def config_show(**kwargs) -> None:
    """Show the current CLI configuration."""
    c = CliConfig()
    config_dump = c._schema.to_dict(redact=True)
    output = kwargs.get("output", "auto")
    verbose = kwargs.get("verbose", False)
    if output == "table":
        table = Table(title="CLI Configuration")
        table.add_column("Field", justify="left")
        table.add_column("Value", justify="left")
        table.add_column("Source", justify="left")
        if output == "table" and verbose:
            for info in c._schema.explain(full_history=True, redact=True):
                # info["history"] is now available for display
                history_str = " → ".join(
                    f"{h['source']}" for h in info.get("history", [])
                )
                table.add_row(info["field"], str(info["value"]), history_str)
        else:
            for field_name, value in config_dump.items():
                source = c._schema._sources.get(field_name, "unknown")
                table.add_row(field_name, str(value) if value is not None else "-", source)
        akcc.console.print(table)
    else:
        akcc.console.formatted_print(config_dump, print_format=output)


@config.command(name="list", requires=["common"])
def config_list(**kwargs) -> None:
    """List all available configuration fields."""
    output = kwargs.get("output", "auto")

    # Build field metadata from the schema
    fields_info = []
    for field_name, fdef in CliConfigSchema._field_defs.items():
        categories = [c for c in fdef.categories.keys() if c != "_bare"]
        fields_info.append({
            "Field": field_name,
            "Type": fdef.type_hint.__name__,
            "Default": str(fdef.default) if fdef.default is not None else "-",
            "Categories": ", ".join(categories) if categories else "-",
        })

    if output == "table":
        table = Table(title="Available configuration fields")
        table.add_column("Field", justify="left")
        table.add_column("Type", justify="left")
        table.add_column("Default", justify="left")
        table.add_column("Categories", justify="left")
        for f in fields_info:
            table.add_row(f["Field"], f["Type"], f["Default"], f["Categories"])
        akcc.console.print(table)
    else:
        akcc.console.formatted_print(fields_info, print_format=output)


@config.command(name="completions", requires=[])
@akcc.argument(
    "shell",
    type=akcc.Choice(["zsh", "bash", "fish"], case_sensitive=True),
    required=True,
)
def config_completions(shell, **kwargs) -> None:
    """Generate auto-completions for the ArmoniK cli"""
    if shell == "zsh":
        akcc.console.print(
            Panel(
                Group(
                    "Add this to your [blue]~/.zshrc[/]\n",
                    Syntax(
                        'eval "$(_ARMONIK_COMPLETE=zsh_source armonik)"',
                        "bash", theme="monokai",
                    ),
                ),
                border_style="blue",
            )
        )
    elif shell == "bash":
        akcc.console.print(
            Panel(
                Group(
                    "Add this to your [blue]~/.bashrc[/]\n",
                    Syntax(
                        'eval "$(_ARMONIK_COMPLETE=bash_source armonik)"',
                        "bash", theme="monokai",
                    ),
                ),
                border_style="blue",
            )
        )
    elif shell == "fish":
        akcc.console.print(
            Panel(
                Group(
                    "Add this to your [blue]~/.config/fish/completions/foo-bar.fish[/]\n",
                    Syntax(
                        "_ARMONIK_COMPLETE=fish_source armonik | source",
                        "bash", theme="monokai",
                    ),
                ),
                border_style="blue",
            )
        )

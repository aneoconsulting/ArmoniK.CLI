import rich_click as click

from armonik.client.versions import ArmoniKVersions
from armonik.client.health_checks import ArmoniKHealthChecks
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print

from armonik_cli_core import console, base_command, base_group
from armonik_cli_core import CliConfig, create_grpc_channel


@click.group(name="cluster")
@base_group
def cluster(**kwargs) -> None:
    """Manage ArmoniK cluster."""
    pass


@cluster.command(name="info")
@base_command(pass_config=True, auto_output="table")
def cluster_info(config: CliConfig, **kwargs) -> None:
    """Get basic information on the ArmoniK cluster (endpoint, versions)"""
    with create_grpc_channel(config) as channel:
        versions_client = ArmoniKVersions(channel)
        version_info = versions_client.list_versions()

        if config.output == "table":
            grid = Table.grid(padding=(0, 1))
            grid.add_column("Label", justify="left", style="cyan", no_wrap=True)
            grid.add_column("Value", style="green", justify="left")

            grid.add_row("Endpoint:", config.endpoint)
            grid.add_row("Core Version:", version_info["core"])
            grid.add_row("API Version:", version_info["api"])

            panel = Panel(grid, title="Cluster Information", border_style="blue")
            print(panel)
        else:
            cluster_info = {
                "Endpoint": config.endpoint,
                "Versions": {"Core": version_info["core"], "API": version_info["api"]},
            }
            console.formatted_print(cluster_info, print_format=config.output)


@cluster.command(name="health")
@base_command(pass_config=True, auto_output="table")
def cluster_health(config: CliConfig, **kwargs) -> None:
    """Get information on the health of some components of the ArmoniK cluster"""
    with create_grpc_channel(config) as channel:
        health_client = ArmoniKHealthChecks(channel)
        health_status = health_client.check_health()

        if config.output == "table":
            grid = Table.grid(padding=(0, 1))
            grid.add_column("Service", style="cyan", justify="left")
            grid.add_column("Status", style="green", justify="left")
            grid.add_column("Message", style="yellow", justify="left")

            for service_name, info in health_status.items():
                status_style = "green" if info["status"] else "red"
                status_text = "✓ Healthy" if info["status"] else "✗ Unhealthy"
                grid.add_row(
                    " ".join(word.capitalize() for word in service_name.split("_")),
                    Text(status_text, style=status_style),
                    info["message"] or "-",
                )

            panel = Panel(grid, title="Health Status", border_style="blue")
            print(panel)
        else:
            console.formatted_print(health_status, print_format=config.output)

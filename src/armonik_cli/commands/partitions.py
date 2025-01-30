import grpc
import rich_click as click

from typing import List, Union

from armonik.client.partitions import ArmoniKPartitions
from armonik.common.filter import Filter, PartitionFilter
from armonik.common import Partition, Direction

from armonik_cli.core import console, base_command, base_group
from armonik_cli.core.params import FilterParam, FieldParam

PARTITIONS_TABLE_COLS = [("ID", "Id"), ("PodReserved", "PodReserved"), ("PodMax", "PodMax")]


@click.group(name="partition")
@base_group
def partitions() -> None:
    """Manage cluster partitions."""
    pass


@partitions.command(name="list")
@click.option(
    "-f",
    "--filter",
    "filter_with",
    type=FilterParam("Partition"),
    required=False,
    help="An expression to filter partitions with",
    metavar="FILTER EXPR",
)
@click.option(
    "--sort-by",
    type=FieldParam("Partition"),
    required=False,
    help="Attribute of partition to sort with.",
)
@click.option(
    "--sort-direction",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    required=False,
    help="Whether to sort by ascending or by descending order.",
)
@click.option(
    "--page", default=-1, help="Get a specific page, it defaults to -1 which gets all pages."
)
@click.option("--page-size", default=100, help="Number of elements in each page")
@base_command
def partition_list(
    endpoint: str,
    output: str,
    filter_with: Union[PartitionFilter, None],
    sort_by: Filter,
    sort_direction: str,
    page: int,
    page_size: int,
    debug: bool,
) -> None:
    """List the partitions in an ArmoniK cluster."""
    with grpc.insecure_channel(endpoint) as channel:
        partitions_client = ArmoniKPartitions(channel)
        curr_page = page if page > 0 else 0
        partitions_list = []
        while True:
            total, partitions = partitions_client.list_partitions(
                partition_filter=filter_with,
                sort_field=Partition.id if sort_by is None else sort_by,
                sort_direction=Direction.ASC
                if sort_direction.capitalize() == "ASC"
                else Direction.DESC,
                page=curr_page,
                page_size=page_size,
            )
            partitions_list += partitions
            if page > 0 or len(partitions_list) >= total:
                break
            curr_page += 1

        if total > 0:
            console.formatted_print(
                partitions_list, format=output, table_cols=PARTITIONS_TABLE_COLS
            )


@partitions.command(name="get")
@click.argument("partition-ids", type=str, nargs=-1, required=True)
@base_command
def partition_get(endpoint: str, output: str, partition_ids: List[str], debug: bool) -> None:
    """Get a specific partition from an ArmoniK cluster given a <PARTITION-ID>."""
    with grpc.insecure_channel(endpoint) as channel:
        partitions_client = ArmoniKPartitions(channel)
        partitions = []
        for partition_id in partition_ids:
            partition = partitions_client.get_partition(partition_id)
            partitions.append(partition)
        console.formatted_print(partitions, format=output, table_cols=PARTITIONS_TABLE_COLS)

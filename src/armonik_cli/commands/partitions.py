import armonik_cli_core as akcc

from typing import List, Optional, Union

from armonik.client.partitions import ArmoniKPartitions
from armonik.common.filter import Filter, PartitionFilter
from armonik.common import Partition, Direction


@akcc.group(name="partition")
def partitions(**kwargs) -> None:
    """Manage cluster partitions."""
    pass


@partitions.command(name="list", pass_config=True, auto_output="table")
@akcc.option(
    "-f",
    "--filter",
    "filter_with",
    type=akcc.FilterParam("Partition"),
    required=False,
    help="An expression to filter partitions with",
    metavar="FILTER EXPR",
)
@akcc.option(
    "--sort-by",
    type=akcc.FieldParam("Partition"),
    required=False,
    help="Attribute of partition to sort with.",
)
@akcc.option(
    "--sort-direction",
    type=akcc.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    required=False,
    help="Whether to sort by ascending or by descending order.",
)
@akcc.option(
    "--page", default=-1, help="Get a specific page, it defaults to -1 which gets all pages."
)
@akcc.option("--page-size", default=100, help="Number of elements in each page")
def partition_list(
    config: akcc.CliConfig,
    filter_with: Union[PartitionFilter, None],
    sort_by: Filter,
    sort_direction: str,
    page: int,
    page_size: int,
    **kwargs,
) -> Optional[List[Partition]]:
    """List the partitions in an ArmoniK cluster."""
    with akcc.create_grpc_channel(config) as channel:
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
            return partitions_list
        return None


@partitions.command(name="get", pass_config=True, auto_output="json")
@akcc.argument("partition-ids", type=str, nargs=-1, required=True)
def partition_get(
    config: akcc.CliConfig, partition_ids: List[str], **kwargs
) -> Optional[List[Partition]]:
    """Get a specific partition from an ArmoniK cluster given a <PARTITION-ID>."""
    with akcc.create_grpc_channel(config) as channel:
        partitions_client = ArmoniKPartitions(channel)
        partitions = []
        for partition_id in partition_ids:
            partition = partitions_client.get_partition(partition_id)
            partitions.append(partition)
        return partitions

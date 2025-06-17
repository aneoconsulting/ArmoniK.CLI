import json
import yaml

from typing import List, Dict, Tuple, Any, Union

from rich.console import Console
from rich.table import Table

from .serialize import serialize


class ArmoniKCLIConsole(Console):
    """
    Custom console that extends the Rich Console to support formatted printing of ArmoniK API objects
    in YAML, JSON, or table formats.
    """

    def formatted_print(
        self, obj: object, print_format: str, table_cols: Union[List[Tuple[str, str]], None] = None
    ) -> None:
        """
        Print an object in a specified format: JSON, YAML, or a table.

        Args:
            obj: The object to format and print.
            print_format: The format in which to print the object. Supported values are 'yaml', 'json', and 'table'.
            table_cols: Columns for the table format as a list of tuples containing the column name and
                corresponding key in the object. Required if format is 'table'.

        Raises:
            ValueError: If `print_format` is 'table' and `table_cols` is not provided.
        """
        obj = serialize(obj)

        if print_format == "yaml":
            obj = yaml.dump(obj, sort_keys=False, indent=2)
        elif print_format == "table":
            if not table_cols:
                raise ValueError(
                    "Missing 'table_cols' when calling 'formatted_print' with format table."
                )
            obj = self._build_table(obj, table_cols)  # type: ignore
        else:
            obj = json.dumps(obj, sort_keys=False, indent=2)

        super().print(obj)

    @staticmethod
    def _build_table(obj: Dict[str, Any], table_cols: List[Tuple[str, str]]) -> Table:
        """
        Build a Rich Table object from a dictionary and column specifications.

        Args:
            obj: The object or list of objects to display in a table.
            table_cols: List of tuples where each tuple contains the table column name and
                the key in `obj` corresponding to the data to display.

        Returns:
            A Rich Table object with the specified columns and rows based on `obj`.
        """
        table = Table(box=None)

        for col_name, _ in table_cols:
            table.add_column(col_name)

        objs = obj if isinstance(obj, List) else [obj]
        for item in objs:
            table.add_row(*[str(item[key]) for _, key in table_cols])

        return table


console = ArmoniKCLIConsole()

from collections import namedtuple
import re

import rich_click as click

from datetime import timedelta
from typing import cast, Tuple, Union
from pathlib import Path

from armonik import common
from armonik.common import Filter
from armonik.common.filter.filter import FType
from lark.exceptions import VisitError

from armonik_cli.utils import parse_time_delta
from .filters import FilterParser, ParsingError


class KeyValuePairParam(click.ParamType):
    """
    A custom Click parameter type that parses a key-value pair in the format "key=value".

    Attributes:
        name: The name of the parameter type, used by Click.
    """

    name = "key_value_pair"

    def convert(
        self, value: str, param: Union[click.Parameter, None], ctx: Union[click.Context, None]
    ) -> Tuple[str, str]:
        """
        Converts the input value into a tuple of (key, value) if it matches the required format.

        Args:
            value: The input value to be converted.
            param: The parameter object passed by Click.
            ctx: The context in which the parameter is being used.

        Returns:
            A tuple (key, value) if the input matches the format "key=value".

        Raises:
            click.BadParameter: If the input does not match the expected format.
        """
        pattern = r"^([a-zA-Z0-9_-]+)=([a-zA-Z0-9_-]+)$"
        match_result = re.match(pattern, value)
        if match_result:
            return cast(Tuple[str, str], match_result.groups())
        self.fail(
            f"{value} is not a valid key value pair. Use key=value where both key and value contain only alphanumeric characters, dashes (-), and underscores (_).",
            param,
            ctx,
        )


class TimeDeltaParam(click.ParamType):
    """
    A custom Click parameter type that parses a time duration string in the format "HH:MM:SS.MS".

    Attributes:
        name: The name of the parameter type, used by Click.
    """

    name = "timedelta"

    def convert(
        self, value: str, param: Union[click.Parameter, None], ctx: Union[click.Context, None]
    ) -> timedelta:
        """
        Converts the input value into a timedelta object if it matches the required time format.

        Args:
            value: The input value to be converted.
            param: The parameter object passed by Click.
            ctx: The context in which the parameter is being used.

        Returns:
            A timedelta object representing the parsed time duration.

        Raises:
            click.BadParameter: If the input does not match the expected time format.
        """
        try:
            return parse_time_delta(value)
        except ValueError:
            self.fail(f"{value} is not a valid time delta. Use HH:MM:SS.MS.", param, ctx)


class FilterParam(click.ParamType):
    """
    A custom Click parameter type that parses a string expression into a valid ArmoniK API filter.

    Attributes:
        name: The name of the parameter type, used by Click.
    """

    name = "filter"

    def __init__(self, filter_type: str) -> None:
        super().__init__()
        try:
            filter_type = filter_type.capitalize()
            from armonik import common

            self.parser = FilterParser(
                obj=getattr(common, filter_type),
                filter=getattr(common.filter, f"{filter_type}Filter"),
                status_enum=getattr(common, f"{filter_type}Status")
                if filter_type != "Partition"
                else None,
                options_fields=(filter_type == "Task" or filter_type == "Session"),
                output_fields=filter_type == "Task",
            )
        except AttributeError:
            msg = f"'{filter_type}' is not a valid filter type."
            raise ValueError(msg)

    def convert(
        self, value: str, param: Union[click.Parameter, None], ctx: Union[click.Context, None]
    ) -> Filter:
        """
        Converts the input value into a valid ArmoniK API filter.

        Args:
            value: The input value to be converted.
            param: The parameter object passed by Click.
            ctx: The context in which the parameter is being used.

        Returns:
            A filter object.

        Raises:
            click.BadParameter: If the input contains a syntax error.
        """
        try:
            return self.parser.parse(value)
        except ParsingError as error:
            self.fail(str(error), param, ctx)
        except VisitError as error:
            self.fail(str(error.orig_exc), param, ctx)


class FieldParam(click.ParamType):
    """
    A custom Click parameter type that validates a field name against the possible fields of a base structure.

    Attributes:
        name: The name of the parameter type, used by Click.
    """

    name = "field"

    def __init__(self, base_struct: str) -> None:
        """
        Initializes the FieldParam instance and gets the fields from the provided base structure.

        Args:
            base_struct: The base structure name to validate fields against (e.g., "Task", "Session").
        """
        super().__init__()
        self.base_struct = base_struct.capitalize()
        cls = getattr(common.filter, f"{self.base_struct}Filter")
        self.possible_fields = [
            field
            for field in cls._fields.keys()
            if cls._fields[field][0] != FType.NA and cls._fields[field][0] != FType.UNKNOWN
        ]

    def convert(
        self, value: str, param: Union[click.Parameter, None], ctx: Union[click.Context, None]
    ) -> Filter:
        """
        Converts the provided value into a field after checking if said value is supported.

         Args:
             value: The input field name to validate.
             param: The parameter object passed by Click.
             ctx: The context in which the parameter is being used.

         Returns:
             A field object.

         Raises:
             click.BadParameter: If the input field is not valid.
        """
        if value not in self.possible_fields:
            self.fail(
                f"{self.base_struct} has no attribute with the name {value}, only valid choices are {','.join(self.possible_fields)}"
            )
        cls = getattr(common, self.base_struct)
        return getattr(cls, value)


class ResultNameDataParam(click.ParamType):
    """Custom Click parameter type that processes and validates result data formats.

    This parameter type handles three different result formats:
    1. Single value: Converts to (value, "nodata")
    2. Bytes data: Converts "name bytes data" to (name, "bytes", bytes_data)
    3. File reference: Converts "name file path" to (name, "file", filepath)

    Attributes:
        name (str): Parameter type name, set to "result"
    """

    name = "result_description"
    ParamType = namedtuple("ParamType", "name type data")

    def convert(
        self, value: str, param: Union[click.Parameter, None], ctx: Union[click.Context, None]
    ) -> Union[ParamType, None]:
        """
        Parses the input value and breaks it down into a tuple after validating it.

        Args:
            value (str): The input string to convert
            param (Union[click.Parameter, None]): Click parameter (optional)
            ctx (Union[click.Context, None]): Click context (optional)

        Returns:
            Union[ParamType, None]: Processed result in one of three formats:
                - (name, "nodata") for single values
                - (name, "bytes", bytes_data) for byte data
                - (name, "file", filepath) for file references
                - None if input is empty

        Raises:
            click.BadParameter: If file doesn't exist or invalid type specified
        """
        if not value:
            return None

        parts = value.split(" ")

        # Validate parts
        if len(parts) == 1:
            return self.ParamType(parts[0], "nodata", None)
        elif len(parts) == 3:
            if parts[1] == "bytes":
                return self.ParamType(parts[0], "bytes", bytes(parts[2], encoding="utf-8"))
            elif parts[1] == "file":
                # check if file exists
                if Path(parts[2]).is_file():
                    return self.ParamType(parts[0], "file", parts[2])
                else:
                    self.fail(
                        f"Couldn't find the file [{parts[2]}] for result data of [{parts[0]}]."
                    )
            else:
                self.fail(
                    f"Invalid type '{parts[1]}'. Must be 'bytes' or 'file'",
                    param,
                    ctx,
                )
        else:
            return None

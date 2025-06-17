import dataclasses

from enum import IntEnum
from datetime import datetime, timedelta
from typing import Dict, List, Union

from armonik_cli.exceptions import ArmoniKCLIError


def to_pascal_case(value: str) -> str:
    """
    Convert snake_case strings to PascalCase.

    Args:
        value: The snake_case string to be converted.

    Returns:
        The PascalCase equivalent of the input string.
    """
    return "".join(word.capitalize() for word in value.split("_"))


SerializerOutput = Union[
    int, bool, float, str, bytes, None, Dict[str, "SerializerOutput"], List["SerializerOutput"]
]


def serialize(obj: object) -> SerializerOutput:
    """
    Converts Python objects into JSON-serializable data structures.

    Handles basic types (str, int, float, bool), collections (dict, list),
    datetime objects, timedelta, IntEnum, dataclasses, as well as ArmoniK specific entities.
    Dict keys must be strings.

    Args:
        obj: Any Python object to serialize

    Returns:
        SerializerOutput: A JSON-serializable structure containing:
            - Basic types (unchanged)
            - Collections with recursively serialized elements
            - Datetime/timedelta as strings
            - IntEnum as capitalized name
            - Dataclass/object fields in PascalCase

    Raises:
        ArmoniKCLIError: If a dict contains non-string keys
    """
    if (
        isinstance(obj, str)
        or type(obj) is int
        or isinstance(obj, float)
        or isinstance(obj, bool)
        or isinstance(obj, bytes)
    ):
        return obj
    elif hasattr(obj, "keys") and hasattr(obj, "values") and hasattr(obj, "items"):
        # Handle protobuf map containers and other dict-like objects
        if all(map(lambda key: isinstance(key, str), obj.keys())):
            return {key: serialize(val) for key, val in obj.items()}
        else:
            raise ArmoniKCLIError(
                "When trying to serialize object, received a dict-like object with a non-string key."
            )
    elif isinstance(obj, timedelta):
        return str(obj)
    elif isinstance(obj, datetime):
        return str(obj)
    elif isinstance(obj, list):
        return [serialize(elem) for elem in obj]
    elif isinstance(obj, IntEnum):
        return obj.name.capitalize()
    elif obj is None:
        return None
    elif dataclasses.is_dataclass(obj):
        return {
            to_pascal_case(field.name): serialize(getattr(obj, field.name))
            for field in dataclasses.fields(obj)
        }
    else:
        # mypy doesn't like the fact that I'm accessing __init__ ... well too bad
        attributes = list(obj.__init__.__annotations__.keys())  # type: ignore
        serialized_object = {
            to_pascal_case(att): serialize(getattr(obj, att)) for att in attributes
        }
        return serialized_object

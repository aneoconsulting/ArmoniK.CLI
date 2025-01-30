from enum import IntEnum
from queue import Queue
from threading import Thread
import time

from typing import Callable, Dict, List, Optional, Generic, Type, TypeVar

import grpc
from armonik_cli.core.input import get_key
import rich_click as click

from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns
from rich.style import Style
from armonik.common import Filter
from armonik.common.filter import TaskFilter, ResultFilter
from armonik.client.events import ArmoniKEvents, EventTypes, Event

Entity = TypeVar("Entity")
EntityStatus = TypeVar("EntityStatus", bound=IntEnum)
EntityFilter = TypeVar("EntityFilter", bound=Filter)


class Watch(Generic[Entity, EntityStatus]):
    """
    A generic class to track the status and data of an entity.

    Attributes:
        status_cls (Type[EntityStatus]): The enum class associated to the status of the watched entity.
        id (str): The unique identifier of the entity.
        data (Entity): The associated entity data.
        status_tracker (Dict[str, List[Dict[str, float]]]): A dictionary tracking the timestamps of status changes.
        current_status (Optional[str]): The current status of the entity.
    """

    status_cls: Type[EntityStatus]

    def __init__(self, identifier, data=None):
        """
        Initializes a Watch instance.

        Args:
            identifier (str): The unique identifier of the entity.
            data (Optional[Entity]): The initial data of the entity.
        """
        if not hasattr(self, "status_cls"):
            raise TypeError(f"{self.__class__.__name__} must define 'status_cls'.")

        self.id: str = identifier
        self._data: Entity = data
        self.status_tracker: Dict[str, List[Dict[str, Optional[float]]]] = {
            field.name: [] for field in self.status_cls
        }
        self._current_status: str = self.status_cls(self.data.status).name if self.data else None

        if self._current_status:
            self.status_tracker[self._current_status].append({"start": time.time(), "end": None})

    @property
    def data(self) -> Entity:
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self.current_status = self.status_cls(value.status).name

    @property
    def current_status(self) -> str:
        return self._current_status

    @current_status.setter
    def current_status(self, value: str):
        """
        Updates the status tracker with a new status change.

        Args:
            new_status (str): The new status to record.
        """
        # For the initial refresh we immediately include the current status in the tracker
        # For subsequent refreshes we only add new ones
        if self._current_status == value and len(self.status_tracker[value]) != 0:
            return
        curr_time = time.time()
        self._current_status = value

        # Record the new status event.
        if not self.status_tracker[value]:
            self.status_tracker[value] = [{"start": curr_time, "end": None}]
        else:
            self.status_tracker[value].append({"start": curr_time, "end": None})

        # Mark the end time for any previous statuses.
        for status, entries in self.status_tracker.items():
            if status == value:
                continue
            if entries and entries[-1]["start"] is not None and entries[-1]["end"] is None:
                entries[-1]["end"] = curr_time

    def refresh(self, client):
        """Refreshes the data of the watched entity via a gRPC call. Must be implemented in subclasses."""
        raise NotImplementedError()


class WatchGroup(Generic[EntityFilter]):
    """
    A watch group creates multiple watch instances and keeps them updated by listening in to ArmoniK events.
    """

    def __init__(
        self,
        endpoint: str,
        debug: bool,
        filter_with: Optional[EntityFilter],
        session_id: Optional[str],
        limit: int,
        entity_ids: Optional[List[str]],
        sort_by: Optional[Filter],
        sort_direction: Optional[str],
    ):
        """
        Initializes a WatchGroup instance.

        Args:
            endpoint (str): The gRPC endpoint.
            debug (bool): Debug mode toggle.
            filter_with (Optional[EntityFilter]): The filter criteria.
            session_id (Optional[str]): The session ID.
            limit (int): The maximum number of entities to watch.
            entity_ids (Optional[List[str]]): List of entity IDs.
            sort_by (Optional[Filter]): Sorting criteria.
            sort_direction (Optional[str]): Sorting direction.
        """
        self.endpoint = endpoint
        self.filter_with = filter_with
        self.entity_ids = entity_ids
        self.limit = limit
        self.debug = debug
        self.sort_by = sort_by
        self.sort_direction = sort_direction
        self.session_id = session_id

        self.watches: Dict[str, Watch] = {}

        self.grpc_channel = grpc.insecure_channel(self.endpoint)

        self._init_populate_watches()

        if not self.session_id:
            session_ids = {watch.data.session_id for watch in self.watches.values()}

            if len(session_ids) > 1:
                raise ValueError(
                    f"Multiple different session_ids found: {session_ids}, if you're using filters, add a session id constraint (or explicitely set it)."
                )

            self.session_id = (
                session_ids.pop()
                if session_ids
                else click.prompt(
                    "We couldn't find any entities that satisfy your filters, enter a session id to automatically watch for and add new entities: "
                )
            )

        self._register_event_handlers()

    def _init_populate_watches(self):
        """Initializes the watches (populate them with data in bulk). Must be implemented in subclasses."""
        raise NotImplementedError()

    def _register_event_handlers(self):
        """Registers event handlers. Must be implemented in subclasses."""
        raise NotImplementedError()

    def get_watches_view(self):
        """Returns a list of watches in the group."""
        return list(self.watches.values())


class WatchDisplay:
    """Handles the display of a single watch entity."""

    def __init__(self, watch: Watch, endpoint: Optional[str] = None):
        """Initializes a WatchDisplay instance."""
        self.watch = watch
        self.endpoint = endpoint

    def display(self):
        """Displays the watch data layout."""
        display_layout = Layout()
        display_layout.split_row(self._create_status_display(), self._create_metadata_display())
        return display_layout


class WatchGroupDisplay:
    """Handles the display of multiple watch entities."""

    def __init__(self, watches: List[Watch], endpoint: Optional[str] = None):
        self.current_tab = 0
        self.watches = watches
        self.endpoint = endpoint

    def update(self):
        """Handles input for navigation between watch tabs."""
        key = get_key(blocking=False)
        if key == "j" or key == "LEFT":
            self.current_tab = (self.current_tab - 1) % len(self.watches)
        elif key == "l" or key == "RIGHT":
            self.current_tab = (self.current_tab + 1) % len(self.watches)
        elif key == "ESCAPE":
            raise click.exceptions.Exit(0)

    def update_contents(self, updated_watches):
        """Updates the watches in the display"""
        self.watches = updated_watches

    def create_navigation_bar(self):
        """Create a navigation bar for switching between watches.
        Returns:
            Columns: A Rich Columns object representing the navigation tabs.
        """
        navigation_tabs = []
        # TODO: flash navigation tab on update
        if self.watches:
            for watch in self.watches:
                tab = Text(f"{watch.id[:6]}..:{watch.current_status}")
                if watch.id == self.watches[self.current_tab].id:
                    tab.stylize(Style(color="black", bgcolor="white", bold=True))
                else:
                    tab.stylize("bold magenta")
                navigation_tabs.append(tab)

        return Columns(navigation_tabs, equal=True, expand=True)

    def create_help_bar(self):
        return Text("ESC to exit, ←/j to move left, →/l to move right")

    def display(self):
        raise NotImplementedError()


def create_nonblocking_event_handler(
    channel: grpc.Channel,
    session_id: str,
    event_types: List[EventTypes],
    event_handlers: List[Callable[[str, EventTypes, Event], bool]],
    task_filter: Optional[TaskFilter] = None,
    result_filter: Optional[ResultFilter] = None,
    exception_queue: Optional[
        Queue
    ] = None,  # TODO: Capture exceptions from threads and handle them in main
):
    """Starts up an event handler in another thread.
    Args:
        channel: gRPC channel to create the event clients in
        session_id: Id of the session whose events we're listening in to
        event_types: List of events that we're listening to
        event_handler: List of callback functions for these events
        task_filter: Optionally whether to filter the tasks whose events we're subscribing to
        result_filter: Optionally whether to filter the results whose events we're subscribing to
    Returns:
        Thread: thread associated to the constructed event handler.
    """

    def _event_handler():
        events_client = ArmoniKEvents(channel)
        events_client.get_events(
            session_id,
            event_types,
            event_handlers,
            task_filter=task_filter,
            result_filter=result_filter,
        )

    event_thread = Thread(target=_event_handler, daemon=True)
    return event_thread

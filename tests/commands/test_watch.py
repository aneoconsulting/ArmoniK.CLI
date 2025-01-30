from threading import Thread
import grpc
import pytest
from unittest.mock import Mock, patch
from enum import IntEnum
from armonik.client import ArmoniKTasks, ArmoniKResults
from armonik.common import TaskStatus, ResultStatus
from armonik.client.events import EventTypes
from armonik_cli.commands.watch import Watch, WatchGroup, create_nonblocking_event_handler
from armonik_cli.commands.tasks import TaskWatch, TasksWatchGroup
from armonik_cli.commands.results import ResultWatch, ResultsWatchGroup


# Sample Enum for testing
class SampleStatus(IntEnum):
    PENDING = 0
    RUNNING = 1
    COMPLETED = 2


# Sample Entity for testing
class SampleEntity:
    def __init__(self, status):
        self.status = status


# Sample Watch subclass
class SampleWatch(Watch[SampleEntity, SampleStatus]):
    status_cls = SampleStatus

    def refresh(self, client):
        pass


@pytest.fixture
def sample_watch():
    return SampleWatch("entity_1", SampleEntity(SampleStatus.PENDING))


# Test Watch class initialization
def test_watch_initialization(sample_watch):
    assert sample_watch.id == "entity_1"
    assert sample_watch.data.status == SampleStatus.PENDING
    assert sample_watch.current_status == "PENDING"
    pending_start_time = sample_watch.status_tracker["PENDING"][0]["start"]
    assert sample_watch.status_tracker == {
        "PENDING": [{"end": None, "start": pending_start_time}],
        "RUNNING": [],
        "COMPLETED": [],
    }


# Test status update
def test_watch_status_update(sample_watch):
    sample_watch.current_status = "RUNNING"
    assert sample_watch.current_status == "RUNNING"
    assert "start" in sample_watch.status_tracker["RUNNING"][-1]


# Test WatchGroup class
def test_watch_group_initialization():
    with patch("grpc.insecure_channel"):
        with pytest.raises(NotImplementedError):
            WatchGroup("localhost", False, None, None, 10, None, None, None)


# Test create_nonblocking_event_handler
def test_create_nonblocking_event_handler():
    channel = Mock()
    session_id = "test_session"
    event_types = [EventTypes.NEW_TASK]
    event_handlers = [lambda s, e, ev: True]

    event_thread = create_nonblocking_event_handler(
        channel, session_id, event_types, event_handlers
    )

    assert isinstance(event_thread, Thread)
    assert event_thread.daemon


# Tests for the non generic watch objects


class StubChannel(grpc.Channel):
    def unary_unary(self, *args, **kwargs):
        """Simulate a unary-unary RPC. Return a callable that does nothing."""

        def fake_rpc(request, timeout=None, metadata=None, credentials=None):
            return None

        return fake_rpc

    def stream_unary(self, *args, **kwargs):
        """Simulate a stream-unary RPC."""

        def fake_stream(requests, timeout=None, metadata=None, credentials=None):
            return None

        return fake_stream

    def unary_stream(self, *args, **kwargs):
        """Simulate a stream-unary RPC."""

        def fake_unary_stream(request, timeout=None, metadata=None, credentials=None):
            yield from []

        return fake_unary_stream

    def stream_stream(self, *args, **kwargs):
        """Simulate a stream-stream RPC."""

        def fake_stream_stream(requests, timeout=None, metadata=None, credentials=None):
            yield from []

        return fake_stream_stream

    def subscribe(self, callback, try_to_connect=False):
        """Subscribe to connectivity changes. No-op."""
        pass

    def unsubscribe(self, callback):
        """Unsubscribe from connectivity changes. No-op."""
        pass

    def close(self):
        """Close the channel. No-op."""
        pass


@pytest.fixture
def patch_grpc_channel(monkeypatch):
    def fake_insecure_channel(endpoint):
        return StubChannel()

    monkeypatch.setattr("grpc.insecure_channel", fake_insecure_channel)


class StubArmoniKEvents:
    def __init__(self, channel):
        self.channel = channel

    def get_events(
        self, session_id, event_types, event_handlers, task_filter=None, result_filter=None
    ):
        pass


@pytest.fixture
def patch_armonik_clients(monkeypatch):
    monkeypatch.setattr("armonik.client.events.ArmoniKEvents", StubArmoniKEvents)


class StubTask:
    """
    Minimal stub simulating the relevant parts of a Task.
    """

    def __init__(self, status, session_id="some_session_id"):
        self.status = status  # e.g., an int from TaskStatus
        self.session_id = session_id

    def refresh(self, client):
        """
        Pretend to do some network call, but actually just updates self.status
        for testing. We'll do something trivial here.
        """
        if self.status == TaskStatus.CREATING:
            self.status = TaskStatus.PROCESSING
        elif self.status == TaskStatus.PROCESSING:
            self.status = TaskStatus.COMPLETED


class StubResult:
    """
    Minimal stub for a real 'Result' object,
    with a .refresh(...) method.
    """

    def __init__(self, result_id, status, session_id="dummy_sess"):
        self.result_id = result_id
        self.status = status
        self.session_id = session_id

    def refresh(self, client):
        """
        Fake a status transition if you want, or do nothing.
        """
        if self.status == ResultStatus.CREATED:
            self.status = ResultStatus.COMPLETED


class StubArmoniKResults:
    def __init__(self, channel):
        self.channel = channel

    def list_results(self, result_filter, page, page_size, sort_field, sort_direction):
        # Return count + list of results
        return (
            2,
            [
                StubResult("resultA", ResultStatus.CREATED, "sessXYZ"),
                StubResult("resultB", ResultStatus.COMPLETED, "sessXYZ"),
            ],
        )

    def get_result(self, result_id):
        return StubResult(result_id, ResultStatus.COMPLETED, "sessXYZ")


@pytest.fixture
def patch_armonik_results_init(monkeypatch):
    """Prevent the real ArmoniKResults from doing gRPC."""

    def fake_init(self, channel):
        # do not set up real stubs
        self.channel = channel
        self._client = None

    monkeypatch.setattr(ArmoniKResults, "__init__", fake_init)


@pytest.fixture
def patch_armonik_results_list(monkeypatch):
    """Patch list_results so no real network call is made."""

    def fake_list_results(self, result_filter, page, page_size, sort_field, sort_direction):
        return StubArmoniKResults(None).list_results(
            result_filter, page, page_size, sort_field, sort_direction
        )

    monkeypatch.setattr(ArmoniKResults, "list_results", fake_list_results)


@pytest.fixture
def patch_armonik_results_get(monkeypatch):
    """Patch get_result for the refresh calls."""

    def fake_get_result(self, result_id):
        return StubArmoniKResults(None).get_result(result_id)

    monkeypatch.setattr(ArmoniKResults, "get_result", fake_get_result)


@pytest.fixture
def patch_armonik_tasks_init(monkeypatch):
    """Prevents ArmoniKTasks from creating a real gRPC client."""

    def fake_init(self, channel):
        # Do not create or assign a real self._client
        self._client = None
        self.channel = channel

    monkeypatch.setattr(ArmoniKTasks, "__init__", fake_init)


@pytest.fixture
def patch_armonik_tasks_list(monkeypatch):
    """Stubs out list_tasks(...) so it doesn't do a real RPC."""

    def fake_list_tasks(self, task_filter, page, page_size, sort_field, sort_direction):
        class FakeTask:
            def __init__(self, id_, status_, session_id):
                self.id = id_
                self.status = status_
                self.session_id = session_id

        return (2, [FakeTask("taskA", 0, "s123"), FakeTask("taskB", 1, "s123")])

    monkeypatch.setattr(ArmoniKTasks, "list_tasks", fake_list_tasks)


@pytest.fixture
def patch_event_handler(monkeypatch):
    def fake_event_handler(*args, **kwargs):
        class FakeThread:
            def start(self_):
                pass  # do nothing

        return FakeThread()

    # Replace the real function
    monkeypatch.setattr(
        "armonik_cli.commands.watch.create_nonblocking_event_handler", fake_event_handler
    )


@pytest.fixture
def stub_task():
    # Start in CREATING status
    return StubTask(status=TaskStatus.CREATING)


def test_task_watch_initialization(stub_task):
    watch = TaskWatch(identifier="task123", data=stub_task)
    assert watch.id == "task123"
    assert watch.current_status == "CREATING"  # from TaskStatus.CREATING


def test_task_watch_status_tracker(stub_task):
    watch = TaskWatch(identifier="task123", data=stub_task)
    # Initially, CREATING status gets recorded
    assert watch.status_tracker["CREATING"]
    assert len(watch.status_tracker["CREATING"]) == 1

    # Simulate changing the underlying task status
    stub_task.status = TaskStatus.PROCESSING
    # Assign watch.data to trigger the setter and status update
    watch.data = stub_task

    assert watch.current_status == "PROCESSING"
    # CREATING has an end time
    assert watch.status_tracker["CREATING"][0]["end"] is not None
    # PROCESSING has a new entry
    assert len(watch.status_tracker["PROCESSING"]) == 1
    assert watch.status_tracker["PROCESSING"][0]["end"] is None


def test_task_watch_refresh(stub_task):
    watch = TaskWatch(identifier="task123", data=stub_task)

    class StubClient:
        pass

    client = StubClient()
    watch.refresh(client)

    # After refresh, we expect the stub task to go from CREATING to PROCESSING
    assert watch.current_status == "PROCESSING"
    # Check the status_tracker for the new transition
    assert watch.status_tracker["CREATING"][0]["end"] is not None
    assert len(watch.status_tracker["PROCESSING"]) == 1


def test_tasks_watch_group_init_with_ids(
    mocker,
    patch_armonik_clients,
    patch_event_handler,
    patch_armonik_tasks_init,
    patch_armonik_tasks_list,
):
    """
    If 'entity_ids' are given, the group shouldn't call list_tasks;
    it should create watchers directly.
    """

    mocker.patch.object(TaskWatch, "refresh", side_effect=lambda client: None)
    group = TasksWatchGroup(
        endpoint="fake_endpoint",
        debug=False,
        filter_with=None,
        session_id="sessXYZ",
        limit=2,
        entity_ids=["taskX", "taskY"],
        sort_by=None,
        sort_direction="asc",
    )

    assert len(group.watches) == 2
    assert isinstance(group.watches["taskX"], TaskWatch)
    assert isinstance(group.watches["taskY"], TaskWatch)


def test_tasks_watch_group_init_no_ids(
    mocker,
    patch_armonik_tasks_init,
    patch_armonik_tasks_list,
    patch_armonik_clients,
    patch_event_handler,
):
    """
    If no entity_ids are provided, ensure the group calls list_tasks.
    """
    mocker.patch.object(TaskWatch, "refresh", side_effect=lambda client: None)

    group = TasksWatchGroup(
        endpoint="fake_endpoint",
        debug=False,
        filter_with=None,
        session_id=None,
        limit=2,
        entity_ids=None,
        sort_by=None,
        sort_direction="asc",
    )

    # The stub returns tasks with session_id="s123", so we check that
    assert len(group.watches) == 2
    assert "taskA" in group.watches
    assert "taskB" in group.watches
    # The group should derive session_id from the tasks
    assert group.session_id == "s123"


def test_tasks_watch_group_event_callbacks(
    mocker,
    patch_armonik_clients,
    patch_event_handler,
    patch_armonik_tasks_init,
    patch_armonik_tasks_list,
):
    """
    Test that event callbacks (update_watch_status, etc.) update watchers.
    """
    mocker.patch.object(TaskWatch, "refresh", side_effect=lambda client: None)

    group = TasksWatchGroup(
        endpoint="fake_endpoint",
        debug=False,
        filter_with=None,
        session_id="my_session",
        limit=2,
        entity_ids=["taskZ"],
        sort_by=None,
        sort_direction="asc",
    )
    # By default, it will create watchers for [taskZ], and refresh them.

    # Add a watch manually for demonstration:
    group.watches["taskZ"].current_status = "CREATING"

    # Simulate an event object
    class StubEvent:
        task_id = "taskZ"
        status = TaskStatus.COMPLETED

    # Fire the update callback
    group.update_watch_status("my_session", EventTypes.TASK_STATUS_UPDATE, StubEvent())
    # Check if the watch was updated
    assert group.watches["taskZ"].current_status == "COMPLETED"


def test_result_watch_init():
    # Start with a stub result in CREATED
    stub = StubResult("result123", ResultStatus.CREATED, "sessID")
    watch = ResultWatch(identifier="result123", data=stub)
    assert watch.id == "result123"
    assert watch.current_status == "CREATED"
    assert watch.data == stub
    # Check initial tracking
    assert len(watch.status_tracker["CREATED"]) == 1


def test_result_watch_refresh():
    stub = StubResult("rX", ResultStatus.CREATED)
    watch = ResultWatch("rX", data=stub)

    # Provide a client stub
    class StubClient:
        def get_result(self, rid):
            # Always return a COMPLETED result
            return StubResult(rid, ResultStatus.COMPLETED, "sessID")

    watch.refresh(StubClient())
    # Should now be COMPLETED
    assert watch.current_status == "COMPLETED"
    assert len(watch.status_tracker["COMPLETED"]) == 1
    # "CREATED" entry should have an end time
    assert watch.status_tracker["CREATED"][0]["end"] is not None


def test_results_watch_group_init_with_ids(
    patch_armonik_results_init,
    patch_armonik_results_list,
    patch_armonik_results_get,
    patch_event_handler,
    patch_grpc_channel,
):
    """
    If 'entity_ids' are given, we do not call list_results;
    watchers are created directly and refresh is called.
    """
    group = ResultsWatchGroup(
        endpoint="fake_endpoint",
        debug=False,
        filter_with=None,
        session_id="sessionXYZ",
        limit=2,
        entity_ids=["r1", "r2"],
        sort_by=None,
        sort_direction="asc",
    )
    assert len(group.watches) == 2
    assert "r1" in group.watches
    assert "r2" in group.watches


def test_results_watch_group_init_no_ids(
    patch_armonik_results_init,
    patch_armonik_results_list,
    patch_armonik_results_get,
    patch_event_handler,
    patch_grpc_channel,
):
    """
    If no entity_ids => we call list_results => returns 2 stubs from our monkeypatch.
    """
    group = ResultsWatchGroup(
        endpoint="fake_endpoint",
        debug=False,
        filter_with=None,
        session_id=None,
        limit=2,
        entity_ids=None,
        sort_by=None,
        sort_direction="asc",
    )
    # Stub returns 2 results: (resultA, resultB) with session_id="sessXYZ"
    assert len(group.watches) == 2
    assert "resultA" in group.watches
    assert "resultB" in group.watches
    assert group.session_id == "sessXYZ"


def test_results_watch_group_event_callback(
    patch_armonik_results_init,
    patch_armonik_results_list,
    patch_armonik_results_get,
    patch_event_handler,
    patch_grpc_channel,
):
    """
    Test that 'update_watch_status' changes watchers for RESULT_STATUS_UPDATE events.
    """
    group = ResultsWatchGroup(
        endpoint="fake_endpoint",
        debug=False,
        filter_with=None,
        session_id="some_sess",
        limit=2,
        entity_ids=["resZ"],
        sort_by=None,
        sort_direction="asc",
    )
    # By default, watch "resZ"
    group.watches["resZ"].current_status = "CREATED"

    class StubEvent:
        result_id = "resZ"
        status = ResultStatus.COMPLETED

    group.update_watch_status("some_sess", EventTypes.RESULT_STATUS_UPDATE, StubEvent())
    assert group.watches["resZ"].current_status == "COMPLETED"

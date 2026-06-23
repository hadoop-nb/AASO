import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from app.core.event_bus import (
    Event,
    EventBus,
    InMemoryEventStore,
    DBEventStore,
    event_bus,
)


@pytest.mark.asyncio
async def test_in_memory_store_store_and_retrieve():
    store = InMemoryEventStore(max_history=10)
    events = [
        Event(event_type="test.a", data={"key": "val"}, source="src1"),
        Event(event_type="test.b", data={"n": 1}, source="src2"),
    ]
    for e in events:
        await store.store(e)

    history = await store.get_history()
    assert len(history) == 2


@pytest.mark.asyncio
async def test_in_memory_store_filter_by_type():
    store = InMemoryEventStore()
    await store.store(Event(event_type="a", data={}, source="s"))
    await store.store(Event(event_type="b", data={}, source="s"))
    await store.store(Event(event_type="a", data={}, source="s"))

    filtered = await store.get_history(event_type="a")
    assert len(filtered) == 2


@pytest.mark.asyncio
async def test_in_memory_store_filter_by_source():
    store = InMemoryEventStore()
    await store.store(Event(event_type="t", data={}, source="src1"))
    await store.store(Event(event_type="t", data={}, source="src2"))

    filtered = await store.get_history(source="src1")
    assert len(filtered) == 1
    assert filtered[0].source == "src1"


@pytest.mark.asyncio
async def test_in_memory_store_max_history():
    store = InMemoryEventStore(max_history=3)
    for i in range(5):
        await store.store(Event(event_type="t", data={"i": i}, source="s"))

    history = await store.get_history()
    assert len(history) == 3
    assert [e.data["i"] for e in history] == [2, 3, 4]


@pytest.mark.asyncio
async def test_in_memory_store_clear():
    store = InMemoryEventStore()
    await store.store(Event(event_type="t", data={}, source="s"))
    await store.store(Event(event_type="t", data={}, source="s"))
    await store.clear()
    history = await store.get_history()
    assert len(history) == 0


@pytest.mark.asyncio
async def test_in_memory_store_limit():
    store = InMemoryEventStore(max_history=100)
    for i in range(20):
        await store.store(Event(event_type="t", data={"i": i}, source="s"))
    limited = await store.get_history(limit=5)
    assert len(limited) == 5


@pytest.mark.asyncio
async def test_db_event_store_store():
    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock()

    store = DBEventStore(mock_repo)
    event = Event(event_type="test", data={"key": "val"}, source="source-1")
    await store.store(event)
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_db_event_store_get_history():
    mock_repo = AsyncMock()
    from app.models.stored_event import StoredEvent

    mock_repo.list_recent = AsyncMock(return_value=[
        StoredEvent(
            event_id="e1", event_type="t", source="s",
            data_json='{"k":"v"}',
            occurred_at=datetime.now(timezone.utc),
        ),
    ])

    store = DBEventStore(mock_repo)
    events = await store.get_history()
    assert len(events) == 1
    assert events[0].event_type == "t"
    assert events[0].data == {"k": "v"}


@pytest.mark.asyncio
async def test_db_event_store_replay():
    mock_repo = AsyncMock()
    from app.models.stored_event import StoredEvent

    mock_repo.replay_events = AsyncMock(return_value=[
        StoredEvent(
            event_id="e1", event_type="t", source="s",
            data_json='{"k":"v"}',
            occurred_at=datetime.now(timezone.utc),
        ),
    ])

    store = DBEventStore(mock_repo)
    events = await store.replay(event_type="t")
    assert len(events) == 1
    mock_repo.replay_events.assert_called_once_with(
        event_type="t", source=None, since=None
    )


@pytest.mark.asyncio
async def test_event_bus_uses_in_memory_store_by_default():
    bus = EventBus()
    await bus.publish(Event(event_type="t", data={}, source="s"))

    assert isinstance(bus._store, InMemoryEventStore)
    history = await bus.get_history()
    assert len(history) == 1


@pytest.mark.asyncio
async def test_event_bus_with_db_store():
    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock()
    mock_repo.list_recent = AsyncMock(return_value=[])

    store = DBEventStore(mock_repo)
    bus = EventBus(store=store)

    await bus.publish(Event(event_type="t", data={"k": "v"}, source="s"))
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_event_bus_set_store():
    bus = EventBus()
    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock()
    store = DBEventStore(mock_repo)
    bus.set_store(store)

    await bus.publish(Event(event_type="t", data={}, source="s"))
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_event_bus_replay_in_memory():
    bus = EventBus()
    for i in range(5):
        await bus.publish(Event(event_type="t", data={"i": i}, source="s"))

    events = await bus.replay()
    assert len(events) == 5


@pytest.mark.asyncio
async def test_event_bus_replay_db():
    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock()
    mock_repo.replay_events = AsyncMock(return_value=[])

    store = DBEventStore(mock_repo)
    bus = EventBus(store=store)

    events = await bus.replay()
    mock_repo.replay_events.assert_called_once()


@pytest.mark.asyncio
async def test_global_event_bus_has_in_memory_store():
    assert isinstance(event_bus._store, InMemoryEventStore)

import pytest

from app.core.event_bus import Event, EventBus


@pytest.fixture
def bus():
    return EventBus()


@pytest.mark.asyncio
async def test_publish_and_subscribe(bus: EventBus):
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe("test.event", handler)
    event = Event(event_type="test.event", data={"key": "value"}, source="test")
    await bus.publish(event)
    assert len(received) == 1
    assert received[0].data["key"] == "value"


@pytest.mark.asyncio
async def test_wildcard_handler(bus: EventBus):
    received = []

    async def handler(event: Event):
        received.append(event.event_type)

    bus.subscribe("*", handler)
    await bus.publish(Event("event.a", {}, "test"))
    await bus.publish(Event("event.b", {}, "test"))
    assert len(received) == 2


@pytest.mark.asyncio
async def test_unsubscribe(bus: EventBus):
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe("test.event", handler)
    bus.unsubscribe("test.event", handler)
    await bus.publish(Event("test.event", {}, "test"))
    assert len(received) == 0


@pytest.mark.asyncio
async def test_get_history(bus: EventBus):
    await bus.publish(Event("a", {"n": 1}, "src1"))
    await bus.publish(Event("b", {"n": 2}, "src2"))
    await bus.publish(Event("a", {"n": 3}, "src1"))

    all_events = bus.get_history()
    assert len(all_events) == 3

    filtered = bus.get_history(event_type="a")
    assert len(filtered) == 2

    filtered = bus.get_history(source="src2")
    assert len(filtered) == 1


@pytest.mark.asyncio
async def test_handler_error_does_not_crash_bus(bus: EventBus):
    called = []

    async def failing(event: Event):
        raise ValueError("oops")

    async def good(event: Event):
        called.append(True)

    bus.subscribe("test", failing)
    bus.subscribe("test", good)
    await bus.publish(Event("test", {}, "src"))
    assert len(called) == 1


@pytest.mark.asyncio
async def test_clear(bus: EventBus):
    await bus.publish(Event("a", {}, "s"))
    bus.clear()
    assert len(bus.get_history()) == 0

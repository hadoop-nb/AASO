from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

EventHandler = Callable[["Event"], Awaitable[None]]


@dataclass
class Event:
    event_type: str
    data: dict
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = ""


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._history: list[Event] = []
        self._max_history = 100

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("Subscribed %s to %s", handler.__name__, event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        handlers = self._handlers.get(event.event_type, []) + self._handlers.get("*", [])
        results = await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True,
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error("Handler %s failed on %s: %s", handler.__name__, event.event_type, result)

    def get_history(
        self,
        event_type: str | None = None,
        source: str | None = None,
        limit: int = 20,
    ) -> list[Event]:
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if source:
            events = [e for e in events if e.source == source]
        return events[-limit:]

    def clear(self) -> None:
        self._history.clear()


event_bus = EventBus()

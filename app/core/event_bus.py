from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
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


class EventStore(ABC):
    @abstractmethod
    async def store(self, event: Event) -> None:
        pass

    @abstractmethod
    async def get_history(
        self,
        event_type: str | None = None,
        source: str | None = None,
        limit: int = 20,
    ) -> list[Event]:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass


class InMemoryEventStore(EventStore):
    def __init__(self, max_history: int = 100):
        self._history: list[Event] = []
        self._max_history = max_history

    async def store(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    async def get_history(
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

    async def clear(self) -> None:
        self._history.clear()


class DBEventStore(EventStore):
    def __init__(self, repository):
        self._repo = repository

    async def store(self, event: Event) -> None:
        from app.models.stored_event import StoredEvent

        stored = StoredEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            source=event.source,
            data_json=json.dumps(event.data, default=str),
            occurred_at=event.timestamp,
        )
        await self._repo.create(stored)

    async def get_history(
        self,
        event_type: str | None = None,
        source: str | None = None,
        limit: int = 20,
    ) -> list[Event]:
        stored = await self._repo.list_recent(
            event_type=event_type,
            source=source,
            limit=limit,
        )
        return [
            Event(
                event_id=e.event_id,
                event_type=e.event_type,
                source=e.source,
                data=json.loads(e.data_json) if e.data_json else {},
                timestamp=e.occurred_at,
            )
            for e in stored
        ]

    async def clear(self) -> None:
        stored = await self._repo.list_recent(limit=10000)
        for e in stored:
            await self._repo.delete(e.event_id)

    async def replay(
        self,
        event_type: str | None = None,
        source: str | None = None,
        since: datetime | None = None,
    ) -> list[Event]:
        stored = await self._repo.replay_events(
            event_type=event_type,
            source=source,
            since=since,
        )
        return [
            Event(
                event_id=e.event_id,
                event_type=e.event_type,
                source=e.source,
                data=json.loads(e.data_json) if e.data_json else {},
                timestamp=e.occurred_at,
            )
            for e in stored
        ]


class EventBus:
    def __init__(self, store: EventStore | None = None) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._store: EventStore = store or InMemoryEventStore()

    def set_store(self, store: EventStore) -> None:
        self._store = store

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("Subscribed %s to %s", handler.__name__, event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: Event) -> None:
        await self._store.store(event)
        handlers = self._handlers.get(event.event_type, []) + self._handlers.get("*", [])
        results = await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True,
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error("Handler %s failed on %s: %s", handler.__name__, event.event_type, result)

    async def get_history(
        self,
        event_type: str | None = None,
        source: str | None = None,
        limit: int = 20,
    ) -> list[Event]:
        return await self._store.get_history(
            event_type=event_type,
            source=source,
            limit=limit,
        )

    async def clear(self) -> None:
        await self._store.clear()

    async def replay(
        self,
        event_type: str | None = None,
        source: str | None = None,
        since: datetime | None = None,
    ) -> list[Event]:
        if isinstance(self._store, DBEventStore):
            return await self._store.replay(
                event_type=event_type,
                source=source,
                since=since,
            )
        return await self.get_history(event_type=event_type, source=source, limit=10000)


event_bus = EventBus()

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stored_event import StoredEvent
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[StoredEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, StoredEvent)

    async def list_by_type(
        self, event_type: str, limit: int = 50, offset: int = 0
    ) -> list[StoredEvent]:
        stmt = (
            select(StoredEvent)
            .where(StoredEvent.event_type == event_type)
            .order_by(StoredEvent.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_source(
        self, source: str, limit: int = 50, offset: int = 0
    ) -> list[StoredEvent]:
        stmt = (
            select(StoredEvent)
            .where(StoredEvent.source == source)
            .order_by(StoredEvent.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(
        self,
        event_type: str | None = None,
        source: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StoredEvent]:
        stmt = select(StoredEvent).order_by(StoredEvent.occurred_at.desc())
        if event_type:
            stmt = stmt.where(StoredEvent.event_type == event_type)
        if source:
            stmt = stmt.where(StoredEvent.source == source)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def replay_events(
        self,
        event_type: str | None = None,
        source: str | None = None,
        since: datetime | None = None,
    ) -> list[StoredEvent]:
        stmt = select(StoredEvent).order_by(StoredEvent.occurred_at.asc())
        if event_type:
            stmt = stmt.where(StoredEvent.event_type == event_type)
        if source:
            stmt = stmt.where(StoredEvent.source == source)
        if since:
            stmt = stmt.where(StoredEvent.occurred_at >= since)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_type(self, event_type: str | None = None) -> int:
        stmt = select(func.count(StoredEvent.event_id))
        if event_type:
            stmt = stmt.where(StoredEvent.event_type == event_type)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_event_type_stats(self) -> list[dict]:
        stmt = (
            select(
                StoredEvent.event_type,
                func.count(StoredEvent.event_id).label("count"),
                func.min(StoredEvent.occurred_at).label("first_seen"),
                func.max(StoredEvent.occurred_at).label("last_seen"),
            )
            .group_by(StoredEvent.event_type)
            .order_by(func.count(StoredEvent.event_id).desc())
        )
        result = await self.session.execute(stmt)
        return [
            {
                "event_type": row.event_type,
                "count": row.count or 0,
                "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            }
            for row in result
        ]

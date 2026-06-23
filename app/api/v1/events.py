from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.event_bus import event_bus, DBEventStore, InMemoryEventStore
from app.repositories.event_repo import EventRepository

router = APIRouter(prefix="/projects/{project_id}/events")


@router.get("")
async def list_events(
    project_id: str,
    event_type: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_db),
):
    from app.core.event_bus import event_bus, DBEventStore, InMemoryEventStore

    if isinstance(event_bus._store, InMemoryEventStore):
        events = await event_bus.get_history(
            event_type=event_type, source=source, limit=limit
        )
        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "source": e.source,
                "data": e.data,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]

    repo = EventRepository(session)
    stored = await repo.list_recent(
        event_type=event_type, source=source, limit=limit
    )
    return [
        {
            "event_id": e.event_id,
            "event_type": e.event_type,
            "source": e.source,
            "data": e.data_json,
            "timestamp": e.occurred_at.isoformat(),
        }
        for e in stored
    ]


@router.get("/replay")
async def replay_events(
    project_id: str,
    event_type: str | None = Query(None),
    source: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
):
    from app.core.event_bus import event_bus, DBEventStore

    if isinstance(event_bus._store, DBEventStore):
        events = await event_bus.replay(
            event_type=event_type, source=source
        )
    else:
        events = await event_bus.get_history(
            event_type=event_type, source=source, limit=10000
        )

    return [
        {
            "event_id": e.event_id,
            "event_type": e.event_type,
            "source": e.source,
            "data": e.data,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in events
    ]


@router.get("/stats")
async def get_event_stats(
    project_id: str,
    session: AsyncSession = Depends(get_db),
):
    from app.core.event_bus import event_bus, DBEventStore

    if isinstance(event_bus._store, DBEventStore):
        repo = EventRepository(session)
        return await repo.get_event_type_stats()

    events = await event_bus.get_history(limit=10000)
    stats: dict[str, dict] = {}
    for e in events:
        if e.event_type not in stats:
            stats[e.event_type] = {"event_type": e.event_type, "count": 0}
        stats[e.event_type]["count"] += 1
    return sorted(stats.values(), key=lambda x: x["count"], reverse=True)

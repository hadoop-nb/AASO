from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics")


@router.get("/agents/stats")
async def agent_stats(
    agent_type: str | None = Query(None),
):
    return await analytics_service.get_agent_stats(agent_type)


@router.get("/projects/{project_id}")
async def project_analytics(
    project_id: str,
    session: AsyncSession = Depends(get_db),
):
    return await analytics_service.get_project_stats(project_id)


@router.get("/runs")
async def recent_runs(
    limit: int = Query(20, ge=1, le=100),
    agent_type: str | None = Query(None),
):
    return await analytics_service.get_recent_runs(limit=limit, agent_type=agent_type)

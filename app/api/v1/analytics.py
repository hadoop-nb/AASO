from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics")


def get_analytics(session: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(session)


@router.get("/agents/stats")
async def agent_stats(
    agent_type: str | None = Query(None),
    analytics: AnalyticsService = Depends(get_analytics),
):
    return await analytics.get_agent_stats(agent_type)


@router.get("/projects/{project_id}")
async def project_analytics(
    project_id: str,
    analytics: AnalyticsService = Depends(get_analytics),
):
    return await analytics.get_project_stats(project_id)


@router.get("/runs")
async def recent_runs(
    limit: int = Query(20, ge=1, le=100),
    agent_type: str | None = Query(None),
    analytics: AnalyticsService = Depends(get_analytics),
):
    return await analytics.get_recent_runs(limit=limit, agent_type=agent_type)


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    analytics: AnalyticsService = Depends(get_analytics),
):
    result = await analytics.get_run(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result

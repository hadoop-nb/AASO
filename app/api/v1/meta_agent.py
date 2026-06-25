from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.meta_agent_service import MetaAgentService

router = APIRouter(prefix="/meta")


@router.post("/retrospective")
async def generate_retrospective(
    project_id: str,
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
):
    svc = MetaAgentService(session)
    analysis = await svc.generate_retrospective(project_id, days)
    return {"analysis_id": analysis.analysis_id, "title": analysis.title}


@router.post("/failure-patterns")
async def mine_failure_patterns(
    project_id: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    svc = MetaAgentService(session)
    analysis = await svc.mine_failure_patterns(project_id)
    return {"analysis_id": analysis.analysis_id, "title": analysis.title}


@router.post("/trends")
async def performance_trends(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db),
):
    svc = MetaAgentService(session)
    analysis = await svc.get_performance_trends(project_id, days)
    return {"analysis_id": analysis.analysis_id, "title": analysis.title}


@router.post("/suggestions")
async def generate_suggestions(
    project_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = MetaAgentService(session)
    analysis = await svc.generate_suggestions(project_id)
    return {"analysis_id": analysis.analysis_id, "title": analysis.title}


@router.get("/analyses")
async def list_analyses(
    project_id: str | None = None,
    analysis_type: str | None = Query(None, pattern="^(retrospective|failure_pattern|trend|suggestion)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    svc = MetaAgentService(session)
    return await svc.get_analyses(project_id, analysis_type, limit, offset)


@router.get("/analyses/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = MetaAgentService(session)
    result = await svc.get_analysis(analysis_id)
    if not result:
        return {"error": "Analysis not found", "analysis_id": analysis_id}
    return result


@router.get("/actionable")
async def get_actionable(
    project_id: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    svc = MetaAgentService(session)
    return await svc.get_actionable(project_id)

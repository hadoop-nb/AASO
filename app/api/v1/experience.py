from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_memory_service
from app.core.database import get_db
from app.services.experience_service import ExperienceService
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/projects/{project_id}/experience")


class FeedbackRequest(BaseModel):
    entity_type: str
    entity_id: str
    score: float
    comment: str = ""


@router.post("/feedback")
async def record_feedback(
    project_id: str,
    request: FeedbackRequest,
    session: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(get_memory_service),
):
    exp = ExperienceService(session, memory)
    await exp.record_feedback(
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        score=request.score,
        comment=request.comment,
    )
    return {"success": True}


@router.get("/top-lessons")
async def top_lessons(
    project_id: str,
    query: str = Query(...),
    limit: int = Query(5, ge=1, le=20),
    session: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(get_memory_service),
):
    exp = ExperienceService(session, memory)
    results = await exp.get_top_lessons(
        project_id=project_id,
        query=query,
        limit=limit,
    )
    return results


@router.get("/top-decisions")
async def top_decisions(
    project_id: str,
    query: str = Query(...),
    limit: int = Query(5, ge=1, le=20),
    session: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(get_memory_service),
):
    exp = ExperienceService(session, memory)
    results = await exp.get_top_decisions(
        project_id=project_id,
        query=query,
        limit=limit,
    )
    return results


@router.get("/stats")
async def experience_stats(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(get_memory_service),
):
    exp = ExperienceService(session, memory)
    return await exp.get_project_stats(project_id)

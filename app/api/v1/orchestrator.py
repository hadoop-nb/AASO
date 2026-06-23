from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_memory_service
from app.core.database import get_db
from app.services.memory_service import MemoryService
from app.services.orchestrator_service import OrchestratorService

router = APIRouter(prefix="/projects/{project_id}/orchestrate")


class OrchestrateRequest(BaseModel):
    goal: str


@router.post("", status_code=201)
async def start_orchestration(
    project_id: str,
    request: OrchestrateRequest,
    session: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(get_memory_service),
):
    try:
        service = OrchestratorService(session, memory=memory)
        result = await service.orchestrate(
            project_id=project_id,
            goal=request.goal,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=400, detail=result.get("error")
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{run_id}")
async def get_orchestration(
    project_id: str,
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    service = OrchestratorService(session)
    run = await service.get_run(project_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run.run_id,
        "project_id": run.project_id,
        "goal": run.goal,
        "status": run.status,
        "sub_tasks": run.sub_tasks,
        "qa_result": run.qa_result,
        "review_result": run.review_result,
        "error": run.error,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }


@router.get("")
async def list_orchestrations(
    project_id: str,
    session: AsyncSession = Depends(get_db),
):
    service = OrchestratorService(session)
    runs = await service.list_runs(project_id)
    return [
        {
            "run_id": r.run_id,
            "goal": r.goal,
            "status": r.status,
            "sub_tasks_count": len(r.sub_tasks),
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]

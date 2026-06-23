from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_decision_service, get_memory_service
from app.schemas.decision import DecisionCreate, DecisionResponse
from app.services.decision_service import DecisionService
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/projects/{project_id}/decisions")


@router.post("", response_model=DecisionResponse, status_code=201)
async def create_decision(
    project_id: str,
    data: DecisionCreate,
    decision_service: DecisionService = Depends(get_decision_service),
    memory_service: MemoryService = Depends(get_memory_service),
):
    decision = await decision_service.create(project_id, data)
    await memory_service.index_entity(
        entity_type="decision",
        entity_id=decision.decision_id,
        project_id=project_id,
        content=f"Question: {data.question}\nSelected: {data.selected}\nReason: {data.reason}",
    )
    return decision


@router.get("", response_model=list[DecisionResponse])
async def list_decisions(
    project_id: str,
    service: DecisionService = Depends(get_decision_service),
):
    return await service.list_by_project(project_id)


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    project_id: str,
    decision_id: str,
    service: DecisionService = Depends(get_decision_service),
):
    decision = await service.get(decision_id)
    if not decision or decision.project_id != project_id:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision

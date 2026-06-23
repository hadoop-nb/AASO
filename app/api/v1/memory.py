from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_memory_service
from app.schemas.memory import MemoryQuery, MemoryResult
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/projects/{project_id}/query")


@router.post("", response_model=list[MemoryResult])
async def query_project_memory(
    project_id: str,
    query: MemoryQuery,
    service: MemoryService = Depends(get_memory_service),
):
    results = await service.query(
        project_id=project_id,
        query=query.query,
        filter_types=query.filter_types,
        limit=query.limit,
    )
    return results

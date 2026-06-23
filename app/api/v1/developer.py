from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_memory_service
from app.core.database import get_db
from app.services.developer_service import DeveloperService
from app.services.memory_service import MemoryService


class ExecuteTaskRequest(BaseModel):
    task_id: str


router = APIRouter(prefix="/agents/developer")


@router.post("/execute")
async def execute_developer(
    project_id: str,
    request: ExecuteTaskRequest,
    session: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(get_memory_service),
):
    try:
        service = DeveloperService(session, memory)
        result = await service.execute_task(
            project_id=project_id,
            task_id=request.task_id,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=400, detail=result.get("error")
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=str(e)
        )

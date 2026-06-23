from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_code_service
from app.schemas.code_file import CodeFileCreate, CodeFileResponse
from app.services.code_service import CodeService

router = APIRouter(prefix="/projects/{project_id}/code")


@router.post("", response_model=CodeFileResponse, status_code=201)
async def create_code_file(
    project_id: str,
    data: CodeFileCreate,
    service: CodeService = Depends(get_code_service),
):
    return await service.create(project_id, data, task_id=data.task_id)


@router.get("", response_model=list[CodeFileResponse])
async def list_code_files(
    project_id: str,
    task_id: str | None = None,
    service: CodeService = Depends(get_code_service),
):
    if task_id:
        return await service.list_by_task(task_id)
    return await service.list_by_project(project_id)


@router.get("/{file_id}", response_model=CodeFileResponse)
async def get_code_file(
    project_id: str,
    file_id: str,
    service: CodeService = Depends(get_code_service),
):
    code_file = await service.get(file_id)
    if not code_file or code_file.project_id != project_id:
        raise HTTPException(
            status_code=404, detail="Code file not found"
        )
    return code_file

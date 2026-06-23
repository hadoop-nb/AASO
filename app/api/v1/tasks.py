from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_task_service
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/projects/{project_id}/tasks")


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    project_id: str,
    data: TaskCreate,
    service: TaskService = Depends(get_task_service),
):
    return await service.create(project_id, data)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    project_id: str,
    service: TaskService = Depends(get_task_service),
):
    return await service.list_by_project(project_id)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    project_id: str,
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    task = await service.get(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    project_id: str,
    task_id: str,
    data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
):
    task = await service.get(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        updated = await service.update(task_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated

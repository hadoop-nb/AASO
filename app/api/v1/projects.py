from fastapi import APIRouter, Depends, HTTPException

from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService
from app.api.deps import get_project_service

router = APIRouter(prefix="/projects")


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
):
    return await service.create(data)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    status: str | None = None,
    service: ProjectService = Depends(get_project_service),
):
    return await service.list(status=status)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    project = await service.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
):
    try:
        project = await service.update(project_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    deleted = await service.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id}/summary")
async def project_summary(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    summary = await service.get_summary(project_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Project not found")
    return summary


@router.get("/{project_id}/report")
async def project_report(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    report = await service.get_report(project_id)
    if not report:
        raise HTTPException(status_code=404, detail="Project not found")
    return report

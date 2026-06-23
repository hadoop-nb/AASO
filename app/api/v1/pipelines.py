from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_memory_service, get_workflow_handlers
from app.core.database import get_db
from app.core.pipeline import PipelineStep, pipeline_runner
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/projects/{project_id}/pipelines")


class PipelineCreateRequest(BaseModel):
    goal: str
    steps: list[dict]


@router.post("", status_code=201)
async def create_pipeline(
    project_id: str,
    request: PipelineCreateRequest,
    session: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(get_memory_service),
):
    handlers = get_workflow_handlers(session, memory)
    for agent_type, handler in handlers.items():
        pipeline_runner.register_handler(agent_type, handler)

    pipeline_id = str(uuid.uuid4())
    pipeline = pipeline_runner.create_pipeline(
        pipeline_id=pipeline_id,
        project_id=project_id,
        goal=request.goal,
        steps=request.steps,
    )
    return {
        "pipeline_id": pipeline.pipeline_id,
        "project_id": pipeline.project_id,
        "goal": pipeline.goal,
        "steps": [{"agent_type": s.agent_type, "config": s.config} for s in pipeline.steps],
    }


@router.post("/{pipeline_id}/start")
async def start_pipeline(
    project_id: str,
    pipeline_id: str,
):
    pipeline = pipeline_runner.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Pipeline not found in project")
    result = await pipeline_runner.start_pipeline(pipeline_id)
    return result


@router.get("/{pipeline_id}")
async def get_pipeline(
    project_id: str,
    pipeline_id: str,
):
    pipeline = pipeline_runner.get_pipeline(pipeline_id)
    if not pipeline or pipeline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {
        "pipeline_id": pipeline.pipeline_id,
        "project_id": pipeline.project_id,
        "goal": pipeline.goal,
        "status": pipeline.status.value,
        "steps": [
            {
                "agent_type": s.agent_type,
                "status": s.status,
                "error": s.error,
            }
            for s in pipeline.steps
        ],
        "created_at": pipeline.created_at.isoformat(),
        "updated_at": pipeline.updated_at.isoformat(),
    }


@router.get("")
async def list_pipelines(
    project_id: str,
):
    pipelines = pipeline_runner.list_pipelines(project_id)
    return [
        {
            "pipeline_id": p.pipeline_id,
            "goal": p.goal,
            "status": p.status.value,
            "steps": len(p.steps),
        }
        for p in pipelines
    ]

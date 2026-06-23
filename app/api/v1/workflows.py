from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_memory_service
from app.core.database import get_db
from app.core.workflow import Workflow, WorkflowEngine, WorkflowStep, WorkflowStatus, workflow_engine
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/projects/{project_id}/workflows")


class WorkflowCreateRequest(BaseModel):
    name: str
    steps: list[dict]


class WorkflowStepResult(BaseModel):
    name: str
    agent_type: str
    status: WorkflowStatus


@router.post("", status_code=201)
async def create_workflow(
    project_id: str,
    request: WorkflowCreateRequest,
    session: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(get_memory_service),
):
    from app.api.deps import get_workflow_handlers

    handlers = get_workflow_handlers(session, memory)
    steps = []
    for step_data in request.steps:
        handler = handlers.get(step_data.get("agent_type", ""))
        if not handler:
            raise HTTPException(status_code=400, detail=f"No handler for agent_type: {step_data.get('agent_type')}")
        steps.append(WorkflowStep(
            name=step_data["name"],
            handler=handler,
            agent_type=step_data.get("agent_type", "unknown"),
            depends_on=step_data.get("depends_on", []),
            max_retries=step_data.get("max_retries", 2),
        ))

    workflow = Workflow(
        workflow_id=str(uuid.uuid4()),
        name=request.name,
        project_id=project_id,
        steps=steps,
    )
    workflow_engine.register(workflow)
    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "project_id": workflow.project_id,
        "steps": [{"name": s.name, "agent_type": s.agent_type, "depends_on": s.depends_on} for s in steps],
    }


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    project_id: str,
    workflow_id: str,
):
    workflow = workflow_engine.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workflow not found in project")
    result = await workflow_engine.execute(workflow_id)
    return result


@router.get("/{workflow_id}")
async def get_workflow(
    project_id: str,
    workflow_id: str,
):
    workflow = workflow_engine.get(workflow_id)
    if not workflow or workflow.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "project_id": workflow.project_id,
        "status": workflow.status.value,
        "steps": [
            {
                "name": s.name,
                "agent_type": s.agent_type,
                "status": s.status.value,
                "error": s.error,
            }
            for s in workflow.steps
        ],
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
    }


@router.get("")
async def list_workflows(
    project_id: str,
):
    workflows = workflow_engine.list_by_project(project_id)
    return [
        {
            "workflow_id": w.workflow_id,
            "name": w.name,
            "status": w.status.value,
            "steps": len(w.steps),
        }
        for w in workflows
    ]


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    project_id: str,
    workflow_id: str,
):
    workflow = workflow_engine.get(workflow_id)
    if not workflow or workflow.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    result = workflow_engine.cancel(workflow_id)
    if not result:
        raise HTTPException(status_code=400, detail="Workflow is not running")
    return {"success": True}

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    name: str
    handler: Callable[..., Awaitable[dict]]
    agent_type: str
    depends_on: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: dict | None = None
    error: str | None = None


@dataclass
class Workflow:
    workflow_id: str
    name: str
    project_id: str
    steps: list[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowEngine:
    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}

    def register(self, workflow: Workflow) -> None:
        self._workflows[workflow.workflow_id] = workflow

    def get(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    def list_by_project(self, project_id: str) -> list[Workflow]:
        return [w for w in self._workflows.values() if w.project_id == project_id]

    async def execute(self, workflow_id: str) -> dict:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return {"success": False, "error": "Workflow not found"}

        workflow.status = WorkflowStatus.RUNNING
        workflow.updated_at = datetime.now(timezone.utc)
        completed: dict[str, dict] = {}

        for step in workflow.steps:
            deps_met = all(dep in completed for dep in step.depends_on)
            if not deps_met:
                step.status = WorkflowStatus.CANCELLED
                continue

            step.status = WorkflowStatus.RUNNING
            for attempt in range(step.max_retries + 1):
                try:
                    kwargs = {dep: completed[dep] for dep in step.depends_on}
                    kwargs["context"] = workflow.context
                    step.result = await step.handler(**kwargs)
                    step.status = WorkflowStatus.COMPLETED
                    completed[step.name] = step.result
                    break
                except Exception as e:
                    step.retry_count = attempt + 1
                    step.error = str(e)
                    if attempt < step.max_retries:
                        logger.warning("Step %s failed (attempt %d/%d): %s", step.name, attempt + 1, step.max_retries + 1, e)
                    else:
                        step.status = WorkflowStatus.FAILED
                        workflow.status = WorkflowStatus.FAILED
                        workflow.updated_at = datetime.now(timezone.utc)
                        return {
                            "success": False,
                            "error": f"Step '{step.name}' failed: {e}",
                            "step_results": completed,
                        }

        workflow.status = WorkflowStatus.COMPLETED
        workflow.updated_at = datetime.now(timezone.utc)
        return {"success": True, "workflow_id": workflow_id, "step_results": completed}

    def cancel(self, workflow_id: str) -> bool:
        workflow = self._workflows.get(workflow_id)
        if not workflow or workflow.status != WorkflowStatus.RUNNING:
            return False
        workflow.status = WorkflowStatus.CANCELLED
        for step in workflow.steps:
            if step.status == WorkflowStatus.PENDING:
                step.status = WorkflowStatus.CANCELLED
        return True


workflow_engine = WorkflowEngine()

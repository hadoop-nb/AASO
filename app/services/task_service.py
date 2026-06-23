from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.lifecycle import validate_task_transition
from app.models.task import Task
from app.repositories.task_repo import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, session: AsyncSession):
        self.repo = TaskRepository(session)

    async def create(
        self, project_id: str, data: TaskCreate
    ) -> Task:
        return await self.repo.create(
            {"project_id": project_id, **data.model_dump()}
        )

    async def get(self, task_id: str) -> Task | None:
        return await self.repo.get(task_id)

    async def update(
        self, task_id: str, data: TaskUpdate
    ) -> Task | None:
        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data:
            current = await self.repo.get(task_id)
            if current and not validate_task_transition(
                current.status, update_data["status"]
            ):
                raise ValueError(
                    f"Invalid transition: {current.status} -> {update_data['status']}"
                )
            if update_data.get("status") == "completed":
                update_data["completion_percentage"] = 100
        return await self.repo.update(task_id, update_data)

    async def list_by_project(
        self, project_id: str
    ) -> list[Task]:
        return await self.repo.list_by_project(project_id)

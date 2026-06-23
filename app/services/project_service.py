from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.lifecycle import validate_project_transition
from app.models.decision import Decision
from app.models.lesson import Lesson
from app.models.project import Project
from app.models.task import Task
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.repo = ProjectRepository(session)
        self.session = session

    async def create(self, data: ProjectCreate) -> Project:
        return await self.repo.create(data.model_dump())

    async def get(self, project_id: str) -> Project | None:
        return await self.repo.get(project_id)

    async def update(
        self, project_id: str, data: ProjectUpdate
    ) -> Project | None:
        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data:
            current = await self.repo.get(project_id)
            if current and not validate_project_transition(
                current.status, update_data["status"]
            ):
                raise ValueError(
                    f"Invalid transition: {current.status} -> {update_data['status']}"
                )
        return await self.repo.update(project_id, update_data)

    async def delete(self, project_id: str) -> bool:
        return await self.repo.delete(project_id)

    async def list(
        self, status: str | None = None
    ) -> list[Project]:
        filters = {}
        if status:
            filters["status"] = status
        return await self.repo.list(filters=filters)

    async def get_summary(self, project_id: str) -> dict:
        stats = await self.repo.get_with_stats(project_id)
        if not stats:
            return None

        project = stats["project"]
        total = stats["total_tasks"]
        total_completion = stats["total_completion"]

        completed_count = len(
            [
                t
                for t in project.tasks
                if t.status == "completed"
            ]
        )
        avg_completion = (
            round(total_completion / total, 1) if total > 0 else 0.0
        )

        return {
            "project_id": project.project_id,
            "name": project.name,
            "status": project.status,
            "total_tasks": total,
            "completed_tasks": completed_count,
            "completion_percentage": avg_completion,
            "total_decisions": len(project.decisions),
            "total_lessons": len(project.lessons),
        }

    async def get_report(self, project_id: str) -> dict:
        project = await self.repo.get_with_related(project_id)
        if not project:
            return None

        tasks = project.tasks
        task_breakdown = {}
        total_completion = 0
        for t in tasks:
            task_breakdown[t.status] = (
                task_breakdown.get(t.status, 0) + 1
            )
            total_completion += t.completion_percentage

        avg_completion = (
            round(total_completion / len(tasks), 1)
            if tasks
            else 0.0
        )

        return {
            "project_id": project.project_id,
            "name": project.name,
            "status": project.status,
            "task_breakdown": task_breakdown,
            "completion_percentage": avg_completion,
            "recent_decisions": [
                {
                    "decision_id": d.decision_id,
                    "question": d.question,
                    "selected": d.selected,
                    "created_at": d.created_at.isoformat(),
                }
                for d in sorted(
                    project.decisions,
                    key=lambda x: x.created_at,
                    reverse=True,
                )[:5]
            ],
            "recent_lessons": [
                {
                    "lesson_id": l.lesson_id,
                    "problem": l.problem,
                    "solution": l.solution,
                    "created_at": l.created_at.isoformat(),
                }
                for l in sorted(
                    project.lessons,
                    key=lambda x: x.created_at,
                    reverse=True,
                )[:5]
            ],
        }

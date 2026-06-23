from sqlalchemy import Integer, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.task import Task
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Project)

    async def get_with_related(self, project_id: str) -> Project | None:
        stmt = (
            select(self.model)
            .where(self.model.project_id == project_id)
            .options(
                selectinload(Project.tasks),
                selectinload(Project.decisions),
                selectinload(Project.lessons),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_with_stats(self, project_id: str) -> dict | None:
        project = await self.get_with_related(project_id)
        if not project:
            return None
        stmt = (
            select(
                func.count(Task.task_id).label("total_tasks"),
                func.coalesce(
                    func.sum(Task.completion_percentage), 0
                ).label("total_completion"),
            )
            .where(Task.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "project": project,
            "total_tasks": row.total_tasks or 0,
            "total_completion": row.total_completion or 0,
        }

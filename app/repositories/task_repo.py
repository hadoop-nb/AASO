from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Task)

    async def list_by_project(
        self, project_id: str
    ) -> list[Task]:
        stmt = (
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

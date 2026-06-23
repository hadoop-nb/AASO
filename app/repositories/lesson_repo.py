from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import Lesson
from app.repositories.base import BaseRepository


class LessonRepository(BaseRepository[Lesson]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Lesson)

    async def list_by_project(
        self, project_id: str
    ) -> list[Lesson]:
        stmt = (
            select(Lesson)
            .where(Lesson.project_id == project_id)
            .order_by(Lesson.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

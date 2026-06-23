from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import Lesson
from app.repositories.lesson_repo import LessonRepository
from app.schemas.lesson import LessonCreate


class LessonService:
    def __init__(self, session: AsyncSession):
        self.repo = LessonRepository(session)

    async def create(
        self, project_id: str, data: LessonCreate
    ) -> Lesson:
        return await self.repo.create(
            {"project_id": project_id, **data.model_dump()}
        )

    async def get(self, lesson_id: str) -> Lesson | None:
        return await self.repo.get(lesson_id)

    async def list_by_project(
        self, project_id: str
    ) -> list[Lesson]:
        return await self.repo.list_by_project(project_id)

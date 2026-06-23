from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_file import CodeFile
from app.repositories.base import BaseRepository


class CodeFileRepository(BaseRepository[CodeFile]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, CodeFile)

    async def list_by_project(
        self, project_id: str
    ) -> list[CodeFile]:
        stmt = (
            select(CodeFile)
            .where(CodeFile.project_id == project_id)
            .order_by(CodeFile.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_task(
        self, task_id: str
    ) -> list[CodeFile]:
        stmt = (
            select(CodeFile)
            .where(CodeFile.task_id == task_id)
            .order_by(CodeFile.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

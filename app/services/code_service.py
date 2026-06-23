from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_file import CodeFile
from app.repositories.code_file_repo import CodeFileRepository
from app.schemas.code_file import CodeFileCreate


class CodeService:
    def __init__(self, session: AsyncSession):
        self.repo = CodeFileRepository(session)

    async def create(
        self,
        project_id: str,
        data: CodeFileCreate,
        task_id: str | None = None,
    ) -> CodeFile:
        return await self.repo.create(
            {
                "project_id": project_id,
                "task_id": task_id,
                **data.model_dump(),
            }
        )

    async def get(self, file_id: str) -> CodeFile | None:
        return await self.repo.get(file_id)

    async def list_by_project(
        self, project_id: str
    ) -> list[CodeFile]:
        return await self.repo.list_by_project(project_id)

    async def list_by_task(
        self, task_id: str
    ) -> list[CodeFile]:
        return await self.repo.list_by_task(task_id)

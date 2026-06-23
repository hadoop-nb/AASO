from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decision import Decision
from app.repositories.decision_repo import DecisionRepository
from app.schemas.decision import DecisionCreate


class DecisionService:
    def __init__(self, session: AsyncSession):
        self.repo = DecisionRepository(session)

    async def create(
        self, project_id: str, data: DecisionCreate
    ) -> Decision:
        return await self.repo.create(
            {"project_id": project_id, **data.model_dump()}
        )

    async def get(self, decision_id: str) -> Decision | None:
        return await self.repo.get(decision_id)

    async def list_by_project(
        self, project_id: str
    ) -> list[Decision]:
        return await self.repo.list_by_project(project_id)

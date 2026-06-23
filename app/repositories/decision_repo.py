from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decision import Decision
from app.repositories.base import BaseRepository


class DecisionRepository(BaseRepository[Decision]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Decision)

    async def list_by_project(
        self, project_id: str
    ) -> list[Decision]:
        stmt = (
            select(Decision)
            .where(Decision.project_id == project_id)
            .order_by(Decision.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

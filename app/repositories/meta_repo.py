from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta_analysis import MetaAnalysis
from app.repositories.base import BaseRepository


class MetaAnalysisRepository(BaseRepository[MetaAnalysis]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MetaAnalysis)

    async def list_by_project(
        self,
        project_id: str,
        analysis_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[MetaAnalysis]:
        stmt = (
            select(MetaAnalysis)
            .where(MetaAnalysis.project_id == project_id)
            .order_by(MetaAnalysis.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if analysis_type:
            stmt = stmt.where(MetaAnalysis.analysis_type == analysis_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(
        self,
        analysis_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[MetaAnalysis]:
        stmt = (
            select(MetaAnalysis)
            .order_by(MetaAnalysis.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if analysis_type:
            stmt = stmt.where(MetaAnalysis.analysis_type == analysis_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_actionable(self, project_id: str | None = None) -> list[MetaAnalysis]:
        stmt = (
            select(MetaAnalysis)
            .where(MetaAnalysis.actionable == True)
            .order_by(MetaAnalysis.created_at.desc())
        )
        if project_id:
            stmt = stmt.where(MetaAnalysis.project_id == project_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_type_stats(self) -> list[dict]:
        stmt = (
            select(
                MetaAnalysis.analysis_type,
                func.count(MetaAnalysis.analysis_id).label("count"),
            )
            .group_by(MetaAnalysis.analysis_type)
            .order_by(func.count(MetaAnalysis.analysis_id).desc())
        )
        result = await self.session.execute(stmt)
        return [{"type": row.analysis_type, "count": row.count} for row in result]

    async def get_recent_trends(
        self, project_id: str, days: int = 30
    ) -> list[MetaAnalysis]:
        from datetime import timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(MetaAnalysis)
            .where(
                MetaAnalysis.project_id == project_id,
                MetaAnalysis.analysis_type == "trend",
                MetaAnalysis.created_at >= cutoff,
            )
            .order_by(MetaAnalysis.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate, AgentAssessment
from app.repositories.base import BaseRepository


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PromptTemplate)

    async def get_active(self, agent_type: str) -> PromptTemplate | None:
        stmt = (
            select(PromptTemplate)
            .where(
                PromptTemplate.agent_type == agent_type,
                PromptTemplate.is_active == True,
            )
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_agent(
        self, agent_type: str, limit: int = 50, offset: int = 0
    ) -> list[PromptTemplate]:
        stmt = (
            select(PromptTemplate)
            .where(PromptTemplate.agent_type == agent_type)
            .order_by(PromptTemplate.version.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_version(self, agent_type: str) -> int:
        stmt = select(func.max(PromptTemplate.version)).where(
            PromptTemplate.agent_type == agent_type
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class AgentAssessmentRepository(BaseRepository[AgentAssessment]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AgentAssessment)

    async def list_by_agent(
        self, agent_type: str, limit: int = 50, offset: int = 0
    ) -> list[AgentAssessment]:
        stmt = (
            select(AgentAssessment)
            .where(AgentAssessment.agent_type == agent_type)
            .order_by(AgentAssessment.executed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_project(
        self, project_id: str, limit: int = 50, offset: int = 0
    ) -> list[AgentAssessment]:
        stmt = (
            select(AgentAssessment)
            .where(AgentAssessment.project_id == project_id)
            .order_by(AgentAssessment.executed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_avg_score_by_agent(self, agent_type: str | None = None) -> list[dict]:
        stmt = select(
            AgentAssessment.agent_type,
            func.count(AgentAssessment.assessment_id).label("count"),
            func.avg(AgentAssessment.score).label("avg_score"),
            func.avg(AgentAssessment.confidence).label("avg_confidence"),
        )
        if agent_type:
            stmt = stmt.where(AgentAssessment.agent_type == agent_type)
        stmt = stmt.group_by(AgentAssessment.agent_type)
        result = await self.session.execute(stmt)
        return [
            {
                "agent_type": row.agent_type,
                "assessments": row.count,
                "avg_score": round(float(row.avg_score or 0), 2),
                "avg_confidence": round(float(row.avg_confidence or 0), 2),
            }
            for row in result
        ]

    async def get_recent_scores_by_agent(
        self, agent_type: str, limit: int = 20
    ) -> list[dict]:
        stmt = (
            select(
                AgentAssessment.score,
                AgentAssessment.confidence,
                AgentAssessment.executed_at,
            )
            .where(AgentAssessment.agent_type == agent_type)
            .order_by(AgentAssessment.executed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "score": row.score,
                "confidence": row.confidence,
                "executed_at": row.executed_at.isoformat() if row.executed_at else None,
            }
            for row in result
        ]

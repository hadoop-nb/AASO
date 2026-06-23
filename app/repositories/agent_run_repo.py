from sqlalchemy import case, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.repositories.base import BaseRepository


class AgentRunRepository(BaseRepository[AgentRun]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AgentRun)

    async def list_by_project(
        self, project_id: str, limit: int = 50, offset: int = 0
    ) -> list[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.project_id == project_id)
            .order_by(AgentRun.executed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_agent_stats(self, agent_type: str | None = None) -> dict:
        success_as_int = case(
            (AgentRun.success.is_(True), 1),
            else_=0,
        ).label("success_int")
        query = select(
            func.count(AgentRun.run_id).label("total"),
            func.sum(success_as_int).label("successes"),
            func.avg(AgentRun.duration_ms).label("avg_duration"),
            func.sum(AgentRun.files_generated).label("total_files"),
        )
        if agent_type:
            query = query.where(AgentRun.agent_type == agent_type)
        result = await self.session.execute(query)
        row = result.one()
        total = row.total or 0
        successes = row.successes or 0
        failures = total - successes
        return {
            "agent_type": agent_type or "all",
            "total_runs": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / total * 100, 1) if total else 0,
            "average_duration_ms": round(float(row.avg_duration or 0), 1),
            "total_files_generated": row.total_files or 0,
        }

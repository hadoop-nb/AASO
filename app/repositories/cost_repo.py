from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_cost import LLMCost
from app.repositories.base import BaseRepository


class CostRepository(BaseRepository[LLMCost]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, LLMCost)

    async def list_by_project(
        self, project_id: str, limit: int = 50, offset: int = 0
    ) -> list[LLMCost]:
        stmt = (
            select(LLMCost)
            .where(LLMCost.project_id == project_id)
            .order_by(LLMCost.executed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_project_cost_summary(self, project_id: str) -> dict:
        stmt = select(
            func.count(LLMCost.cost_id).label("total_calls"),
            func.sum(LLMCost.total_tokens).label("total_tokens"),
            func.sum(LLMCost.cost_usd).label("total_cost"),
            func.sum(LLMCost.prompt_tokens).label("total_prompt_tokens"),
            func.sum(LLMCost.completion_tokens).label("total_completion_tokens"),
        ).where(LLMCost.project_id == project_id)
        result = await self.session.execute(stmt)
        row = result.one()
        total_tokens = row.total_tokens or 0
        return {
            "project_id": project_id,
            "total_calls": row.total_calls or 0,
            "total_tokens": total_tokens,
            "total_prompt_tokens": row.total_prompt_tokens or 0,
            "total_completion_tokens": row.total_completion_tokens or 0,
            "total_cost_usd": round(float(row.total_cost or 0), 6),
        }

    async def get_overall_stats(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        stmt = select(
            func.count(LLMCost.cost_id).label("total_calls"),
            func.sum(LLMCost.total_tokens).label("total_tokens"),
            func.sum(LLMCost.cost_usd).label("total_cost"),
            func.avg(LLMCost.cost_usd).label("avg_cost_per_call"),
            func.count(LLMCost.project_id.distinct()).label("projects_using_llm"),
        )
        if start_date:
            stmt = stmt.where(LLMCost.executed_at >= start_date)
        if end_date:
            stmt = stmt.where(LLMCost.executed_at <= end_date)
        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "total_calls": row.total_calls or 0,
            "total_tokens": row.total_tokens or 0,
            "total_cost_usd": round(float(row.total_cost or 0), 6),
            "avg_cost_per_call_usd": round(float(row.avg_cost_per_call or 0), 6),
            "projects_using_llm": row.projects_using_llm or 0,
        }

    async def get_cost_by_model(self) -> list[dict]:
        stmt = (
            select(
                LLMCost.model,
                func.count(LLMCost.cost_id).label("calls"),
                func.sum(LLMCost.total_tokens).label("total_tokens"),
                func.sum(LLMCost.cost_usd).label("total_cost"),
            )
            .group_by(LLMCost.model)
            .order_by(func.sum(LLMCost.cost_usd).desc())
        )
        result = await self.session.execute(stmt)
        return [
            {
                "model": row.model,
                "total_calls": row.calls or 0,
                "total_tokens": row.total_tokens or 0,
                "total_cost_usd": round(float(row.total_cost or 0), 6),
            }
            for row in result
        ]

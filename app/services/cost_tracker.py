from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_cost import LLMCost
from app.repositories.cost_repo import CostRepository

logger = logging.getLogger(__name__)

MODEL_COST_PER_1K_TOKENS: dict[str, float] = {
    "big-pickle": 0.0,
    "deepseek-v4-flash-free": 0.0,
    "mimo-v2.5-free": 0.0,
    "north-mini-code-free": 0.0,
    "nemotron-3-ultra-free": 0.0,
    "llama3.2": 0.0,
    "stub": 0.0,
}


class CostTracker:
    def __init__(self, session: AsyncSession | None = None):
        self._session = session
        self._repo: CostRepository | None = None
        self._costs: list[LLMCost] = []

    def set_session(self, session: AsyncSession):
        self._session = session
        self._repo = CostRepository(session)

    async def record_call(
        self,
        model: str,
        provider: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        project_id: str | None = None,
        agent_type: str | None = None,
        prompt: str | None = None,
        response: str | None = None,
    ) -> LLMCost:
        total_tokens = prompt_tokens + completion_tokens
        rate = MODEL_COST_PER_1K_TOKENS.get(model, 0.0)
        cost_usd = (total_tokens / 1000) * rate if rate > 0 else 0.0

        record = LLMCost(
            cost_id="",
            project_id=project_id,
            agent_type=agent_type,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            prompt=prompt,
            response=response,
            executed_at=datetime.now(timezone.utc),
        )

        if self._repo:
            created = await self._repo.create(record)
            self._costs.append(record)
            return created

        self._costs.append(record)
        return record

    def get_cached_costs(self) -> list[LLMCost]:
        return self._costs

    async def get_project_summary(self, project_id: str) -> dict:
        if self._repo:
            return await self._repo.get_project_cost_summary(project_id)
        return {"project_id": project_id, "total_calls": 0, "total_tokens": 0, "total_cost_usd": 0.0}

    async def get_overall_stats(self) -> dict:
        if self._repo:
            return await self._repo.get_overall_stats()
        return {"total_calls": 0, "total_tokens": 0, "total_cost_usd": 0.0}

    async def get_cost_by_model(self) -> list[dict]:
        if self._repo:
            return await self._repo.get_cost_by_model()
        return []

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


cost_tracker = CostTracker()

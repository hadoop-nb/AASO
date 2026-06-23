from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import Integer, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.code_file import CodeFile

logger = logging.getLogger(__name__)


@dataclass
class AgentRunRecord:
    agent_type: str
    project_id: str
    task_id: str
    success: bool
    duration_ms: float
    files_generated: int = 0
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AnalyticsService:
    def __init__(self, session: AsyncSession | None = None):
        self.session = session
        self._runs: list[AgentRunRecord] = []

    def record_run(self, record: AgentRunRecord) -> None:
        self._runs.append(record)

    async def get_agent_stats(self, agent_type: str | None = None) -> dict:
        runs = self._runs
        if agent_type:
            runs = [r for r in runs if r.agent_type == agent_type]

        total = len(runs)
        if total == 0:
            return {"total_runs": 0, "agent_type": agent_type or "all"}

        successes = sum(1 for r in runs if r.success)
        failures = total - successes
        avg_duration = sum(r.duration_ms for r in runs) / total
        total_files = sum(r.files_generated for r in runs)
        success_rate = round(successes / total * 100, 1)

        return {
            "agent_type": agent_type or "all",
            "total_runs": total,
            "successes": successes,
            "failures": failures,
            "success_rate": success_rate,
            "average_duration_ms": round(avg_duration, 1),
            "total_files_generated": total_files,
        }

    async def get_project_stats(self, project_id: str) -> dict:
        runs = [r for r in self._runs if r.project_id == project_id]
        total = len(runs)
        if total == 0:
            return {"project_id": project_id, "total_runs": 0}

        successes = sum(1 for r in runs if r.success)
        avg_duration = sum(r.duration_ms for r in runs) / total

        agent_types = set(r.agent_type for r in runs)
        per_agent = {}
        for at in agent_types:
            agent_runs = [r for r in runs if r.agent_type == at]
            per_agent[at] = {
                "runs": len(agent_runs),
                "successes": sum(1 for r in agent_runs if r.success),
            }

        completion_rate = 0.0
        avg_files = 0.0
        if self.session:
            try:
                result = await self.session.execute(
                    select(
                        func.avg(Task.completion_percentage).label("avg_completion"),
                    ).where(Task.project_id == project_id)
                )
                row = result.one()
                if row.avg_completion:
                    completion_rate = round(row.avg_completion, 1)
                file_result = await self.session.execute(
                    select(func.count(CodeFile.file_id)).where(CodeFile.project_id == project_id)
                )
                avg_files = file_result.scalar() or 0
            except Exception as exc:
                logger.warning("Could not fetch DB stats: %s", exc)

        return {
            "project_id": project_id,
            "total_runs": total,
            "successes": successes,
            "success_rate": round(successes / total * 100, 1) if total else 0,
            "average_duration_ms": round(avg_duration, 1),
            "per_agent": per_agent,
            "completion_rate": completion_rate,
            "total_code_files": avg_files,
        }

    async def get_recent_runs(
        self,
        limit: int = 20,
        agent_type: str | None = None,
    ) -> list[dict]:
        runs = self._runs
        if agent_type:
            runs = [r for r in runs if r.agent_type == agent_type]
        runs = runs[-limit:]
        return [
            {
                "agent_type": r.agent_type,
                "project_id": r.project_id,
                "task_id": r.task_id,
                "success": r.success,
                "duration_ms": r.duration_ms,
                "files_generated": r.files_generated,
                "error": r.error,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in reversed(runs)
        ]


analytics_service = AnalyticsService()

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.code_file import CodeFile
from app.models.task import Task
from app.repositories.agent_run_repo import AgentRunRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, session: AsyncSession | None = None):
        self.session = session
        self._repo: AgentRunRepository | None = None

    def _ensure_repo(self) -> AgentRunRepository:
        if not self._repo and self.session:
            self._repo = AgentRunRepository(self.session)
        return self._repo

    async def record_run(
        self,
        agent_type: str,
        agent_id: str,
        project_id: str,
        task_id: str,
        success: bool,
        duration_ms: float,
        files_generated: int = 0,
        error: str | None = None,
        result_summary: str | None = None,
        metadata: dict | None = None,
    ) -> AgentRun | None:
        repo = self._ensure_repo()
        if not repo:
            return None
        run = await repo.create({
            "agent_type": agent_type,
            "agent_id": agent_id,
            "project_id": project_id,
            "task_id": task_id,
            "success": success,
            "duration_ms": duration_ms,
            "files_generated": files_generated,
            "error": error,
            "result_summary": result_summary,
            "metadata_json": json.dumps(metadata) if metadata else None,
            "executed_at": datetime.now(timezone.utc),
        })
        return run

    async def get_agent_stats(self, agent_type: str | None = None) -> dict:
        repo = self._ensure_repo()
        if not repo:
            return {"total_runs": 0, "agent_type": agent_type or "all"}
        return await repo.get_agent_stats(agent_type)

    async def get_project_stats(self, project_id: str) -> dict:
        repo = self._ensure_repo()
        if not repo:
            return {"project_id": project_id, "total_runs": 0}

        runs = await repo.list_by_project(project_id, limit=10000)
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
        repo = self._ensure_repo()
        if not repo:
            return []

        stmt = select(AgentRun).order_by(AgentRun.executed_at.desc()).limit(limit)
        if agent_type:
            stmt = stmt.where(AgentRun.agent_type == agent_type)
        result = await self.session.execute(stmt)
        runs = list(result.scalars().all())
        return [
            {
                "run_id": r.run_id,
                "agent_type": r.agent_type,
                "agent_id": r.agent_id,
                "project_id": r.project_id,
                "task_id": r.task_id,
                "success": r.success,
                "duration_ms": r.duration_ms,
                "files_generated": r.files_generated,
                "error": r.error,
                "result_summary": r.result_summary,
                "timestamp": r.executed_at.isoformat(),
            }
            for r in runs
        ]

    async def get_run(self, run_id: str) -> dict | None:
        repo = self._ensure_repo()
        if not repo:
            return None
        run = await repo.get(run_id)
        if not run:
            return None
        return {
            "run_id": run.run_id,
            "agent_type": run.agent_type,
            "agent_id": run.agent_id,
            "project_id": run.project_id,
            "task_id": run.task_id,
            "success": run.success,
            "duration_ms": run.duration_ms,
            "files_generated": run.files_generated,
            "error": run.error,
            "result_summary": run.result_summary,
            "metadata": json.loads(run.metadata_json) if run.metadata_json else None,
            "executed_at": run.executed_at.isoformat(),
        }


analytics_service = AnalyticsService()

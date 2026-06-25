from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, case, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta_analysis import MetaAnalysis
from app.models.agent_run import AgentRun
from app.repositories.meta_repo import MetaAnalysisRepository

logger = logging.getLogger(__name__)


class MetaAgentService:
    def __init__(self, session: AsyncSession):
        self._repo = MetaAnalysisRepository(session)
        self._session = session

    async def generate_retrospective(
        self, project_id: str, days: int = 7
    ) -> MetaAnalysis:
        """Generate a retrospective for a project over the given period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = (
            select(AgentRun)
            .where(
                AgentRun.project_id == project_id,
                AgentRun.executed_at >= cutoff,
            )
            .order_by(AgentRun.executed_at.desc())
        )
        result = await self._session.execute(stmt)
        runs = list(result.scalars().all())

        total_runs = len(runs)
        successful = sum(1 for r in runs if r.success)
        failed = total_runs - successful
        success_rate = (successful / total_runs * 100) if total_runs > 0 else 0.0
        avg_duration = (
            sum(r.duration_ms for r in runs if r.duration_ms) / total_runs
            if total_runs > 0
            else 0.0
        )

        runs_by_agent: dict[str, int] = {}
        runs_by_type: dict[str, int] = {}
        failures_by_type: dict[str, int] = {}
        for r in runs:
            runs_by_agent[r.agent_type] = runs_by_agent.get(r.agent_type, 0) + 1
            runs_by_type[r.agent_type] = runs_by_type.get(r.agent_type, 0) + 1
            if not r.success:
                failures_by_type[r.agent_type] = (
                    failures_by_type.get(r.agent_type, 0) + 1
                )

        details = {
            "period_days": days,
            "total_runs": total_runs,
            "successful": successful,
            "failed": failed,
            "success_rate_pct": round(success_rate, 1),
            "avg_duration_ms": round(avg_duration, 0),
            "runs_by_agent_type": runs_by_type,
            "failures_by_agent_type": failures_by_type,
            "recent_errors": [
                {
                    "run_id": r.run_id,
                    "agent_type": r.agent_type,
                    "error": r.error,
                    "executed_at": r.executed_at.isoformat() if r.executed_at else None,
                }
                for r in runs[:10]
                if not r.success and r.error
            ],
        }

        summary_lines = [
            f"Retrospective for project {project_id} over the last {days} day(s).",
            f"Total runs: {total_runs} | Success rate: {success_rate:.1f}% | "
            f"Avg duration: {avg_duration:.0f}ms",
        ]
        if failures_by_type:
            worst = max(failures_by_type, key=failures_by_type.get)
            summary_lines.append(
                f"Most failures from agent type: {worst} "
                f"({failures_by_type[worst]} failures)"
            )

        return await self._repo.create({
            "project_id": project_id,
            "analysis_type": "retrospective",
            "title": f"Retrospective ({days}d): {success_rate:.0f}% success rate",
            "summary": "\n".join(summary_lines),
            "details_json": json.dumps(details),
            "period_start": cutoff,
            "period_end": datetime.now(timezone.utc),
            "actionable": failed > 0,
        })

    async def mine_failure_patterns(
        self, project_id: str | None = None
    ) -> MetaAnalysis:
        """Mine failure patterns from agent runs."""
        stmt = select(
            AgentRun.agent_type,
            func.count(AgentRun.run_id).label("total"),
            func.sum(
                case((AgentRun.success == False, 1), else_=0).cast(Integer)
            ).label("failures"),
        )
        if project_id:
            stmt = stmt.where(AgentRun.project_id == project_id)
        stmt = stmt.group_by(AgentRun.agent_type)
        result = await self._session.execute(stmt)
        rows = result.fetchall()

        patterns = []
        for row in rows:
            total = row.total or 0
            failures = row.failures or 0
            rate = (failures / total * 100) if total > 0 else 0
            patterns.append({
                "agent_type": row.agent_type,
                "total_runs": total,
                "failures": failures,
                "failure_rate_pct": round(rate, 1),
            })

        patterns.sort(key=lambda p: p["failure_rate_pct"], reverse=True)

        top_type = patterns[0] if patterns else None
        summary_lines = []
        if top_type and top_type["failure_rate_pct"] > 0:
            summary_lines.append(
                f"Highest failure rate: {top_type['agent_type']} "
                f"({top_type['failure_rate_pct']}%)"
            )

        high_failure = [p for p in patterns if p["failure_rate_pct"] > 20]
        if high_failure:
            summary_lines.append(
                f"{len(high_failure)} agent type(s) exceed 20% failure threshold"
            )

        if not summary_lines:
            summary_lines.append("No significant failure patterns detected.")

        return await self._repo.create({
            "project_id": project_id,
            "analysis_type": "failure_pattern",
            "title": f"Failure Pattern Analysis: {len(patterns)} agent types",
            "summary": "\n".join(summary_lines),
            "details_json": json.dumps({"patterns": patterns}),
            "actionable": bool(high_failure),
        })

    async def get_performance_trends(
        self, project_id: str, days: int = 30
    ) -> MetaAnalysis:
        """Analyze performance trends over time."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = (
            select(
                AgentRun.agent_type,
                func.date(AgentRun.executed_at).label("day"),
                func.count(AgentRun.run_id).label("runs"),
                func.avg(AgentRun.duration_ms).label("avg_duration"),
                func.sum(
                    case((AgentRun.success == False, 1), else_=0).cast(Integer)
                ).label("failures"),
            )
            .where(
                AgentRun.project_id == project_id,
                AgentRun.executed_at >= cutoff,
            )
            .group_by(AgentRun.agent_type, func.date(AgentRun.executed_at))
            .order_by(func.date(AgentRun.executed_at))
        )
        result = await self._session.execute(stmt)
        rows = result.fetchall()

        trends = []
        for row in rows:
            total = row.runs or 0
            failures = row.failures or 0
            trends.append({
                "agent_type": row.agent_type,
                "date": str(row.day),
                "runs": total,
                "avg_duration_ms": round(row.avg_duration or 0, 0),
                "failure_rate_pct": round((failures / total * 100) if total > 0 else 0, 1),
            })

        summary = (
            f"Trend analysis over {days} days: {len(trends)} data points across "
            f"{len(set(t['agent_type'] for t in trends))} agent types"
        )

        return await self._repo.create({
            "project_id": project_id,
            "analysis_type": "trend",
            "title": f"Performance Trends ({days}d)",
            "summary": summary,
            "details_json": json.dumps({"trends": trends, "days": days}),
            "period_start": cutoff,
            "period_end": datetime.now(timezone.utc),
            "actionable": False,
        })

    async def generate_suggestions(
        self, project_id: str
    ) -> MetaAnalysis:
        """Generate actionable suggestions based on failure patterns and trends."""
        failure = await self.mine_failure_patterns(project_id)
        details = json.loads(failure.details_json) if failure.details_json else {}
        patterns = details.get("patterns", [])

        suggestions = []
        for p in patterns:
            if p["failure_rate_pct"] > 20:
                suggestions.append({
                    "agent_type": p["agent_type"],
                    "suggestion": (
                        f"High failure rate ({p['failure_rate_pct']}%) for "
                        f"{p['agent_type']}. Review prompts and error handling."
                    ),
                    "priority": "high" if p["failure_rate_pct"] > 40 else "medium",
                })

        if not suggestions:
            suggestions.append({
                "agent_type": "general",
                "suggestion": "No critical issues detected. Continue monitoring.",
                "priority": "low",
            })

        summary = f"Generated {len(suggestions)} suggestion(s) for project {project_id}."

        return await self._repo.create({
            "project_id": project_id,
            "analysis_type": "suggestion",
            "title": f"Improvement Suggestions ({len(suggestions)} items)",
            "summary": summary,
            "details_json": json.dumps({"suggestions": suggestions}),
            "actionable": True,
        })

    async def get_analyses(
        self,
        project_id: str | None = None,
        analysis_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        if project_id:
            analyses = await self._repo.list_by_project(
                project_id, analysis_type, limit, offset
            )
        else:
            analyses = await self._repo.list_recent(analysis_type, limit, offset)
        return [self._to_dict(a) for a in analyses]

    async def get_analysis(self, analysis_id: str) -> dict | None:
        analysis = await self._repo.get(analysis_id)
        return self._to_dict(analysis) if analysis else None

    async def get_actionable(
        self, project_id: str | None = None
    ) -> list[dict]:
        analyses = await self._repo.get_actionable(project_id)
        return [self._to_dict(a) for a in analyses]

    def _to_dict(self, a: MetaAnalysis) -> dict:
        return {
            "analysis_id": a.analysis_id,
            "project_id": a.project_id,
            "analysis_type": a.analysis_type,
            "title": a.title,
            "summary": a.summary,
            "details": json.loads(a.details_json) if a.details_json else None,
            "period_start": a.period_start.isoformat() if a.period_start else None,
            "period_end": a.period_end.isoformat() if a.period_end else None,
            "actionable": a.actionable,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }

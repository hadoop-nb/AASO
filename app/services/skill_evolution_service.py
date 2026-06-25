from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate, AgentAssessment
from app.repositories.skill_repo import (
    PromptTemplateRepository,
    AgentAssessmentRepository,
)

logger = logging.getLogger(__name__)


class SkillEvolutionService:
    def __init__(self, session: AsyncSession):
        self._prompt_repo = PromptTemplateRepository(session)
        self._assessment_repo = AgentAssessmentRepository(session)
        self._session = session

    async def record_assessment(
        self,
        agent_type: str,
        agent_id: str,
        score: float,
        confidence: float = 1.0,
        run_id: str | None = None,
        task_id: str | None = None,
        project_id: str | None = None,
        strengths: str | None = None,
        weaknesses: str | None = None,
        notes: str | None = None,
    ) -> AgentAssessment:
        if not 0 <= score <= 10:
            raise ValueError("Score must be between 0 and 10")
        if not 0 <= confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")

        return await self._assessment_repo.create({
            "run_id": run_id,
            "agent_type": agent_type,
            "agent_id": agent_id,
            "task_id": task_id,
            "project_id": project_id,
            "score": score,
            "confidence": confidence,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "notes": notes,
        })

    async def get_agent_performance(
        self, agent_type: str | None = None
    ) -> list[dict]:
        return await self._assessment_repo.get_avg_score_by_agent(agent_type)

    async def get_assessment_history(
        self,
        agent_type: str | None = None,
        project_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        if project_id:
            assessments = await self._assessment_repo.list_by_project(
                project_id, limit, offset
            )
        elif agent_type:
            assessments = await self._assessment_repo.list_by_agent(
                agent_type, limit, offset
            )
        else:
            assessments = await self._assessment_repo.list(
                limit=limit, offset=offset,
                order_by="executed_at"
            )
        return [self._assessment_to_dict(a) for a in assessments]

    async def create_prompt_template(
        self,
        agent_type: str,
        name: str,
        system_prompt: str,
        user_prompt_template: str | None = None,
        change_notes: str | None = None,
    ) -> PromptTemplate:
        latest_version = await self._prompt_repo.get_latest_version(agent_type)
        new_version = latest_version + 1

        current_active = await self._prompt_repo.get_active(agent_type)
        if current_active:
            await self._prompt_repo.update(
                current_active.template_id, {"is_active": False}
            )

        return await self._prompt_repo.create({
            "agent_type": agent_type,
            "version": new_version,
            "name": name,
            "system_prompt": system_prompt,
            "user_prompt_template": user_prompt_template,
            "is_active": True,
            "change_notes": change_notes,
        })

    async def get_active_prompt(self, agent_type: str) -> dict | None:
        template = await self._prompt_repo.get_active(agent_type)
        return self._prompt_to_dict(template) if template else None

    async def list_prompt_templates(
        self, agent_type: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        if agent_type:
            templates = await self._prompt_repo.list_by_agent(agent_type, limit, offset)
        else:
            templates = await self._prompt_repo.list(limit=limit, offset=offset)
        return [self._prompt_to_dict(t) for t in templates]

    async def compare_ab_test(
        self, agent_type: str, version_a: int, version_b: int
    ) -> dict:
        templates = await self._prompt_repo.list_by_agent(agent_type)
        tpl_map = {t.version: t for t in templates}

        tpl_a = tpl_map.get(version_a)
        tpl_b = tpl_map.get(version_b)
        if not tpl_a or not tpl_b:
            return {"error": "One or both template versions not found"}

        a_assessments = await self._assessment_repo.list_by_agent(
            agent_type, limit=100
        )
        a_scores = [a.score for a in a_assessments]

        return {
            "version_a": self._prompt_to_dict(tpl_a),
            "version_b": self._prompt_to_dict(tpl_b),
            "comparison": {
                "version_a_assessments": len(a_scores),
                "version_a_avg_score": round(
                    sum(a_scores) / len(a_scores), 2
                ) if a_scores else None,
                "version_a_assessment_count": len(a_scores),
            },
        }

    def _assessment_to_dict(self, a: AgentAssessment) -> dict:
        return {
            "assessment_id": a.assessment_id,
            "run_id": a.run_id,
            "agent_type": a.agent_type,
            "agent_id": a.agent_id,
            "task_id": a.task_id,
            "project_id": a.project_id,
            "score": a.score,
            "confidence": a.confidence,
            "strengths": a.strengths,
            "weaknesses": a.weaknesses,
            "notes": a.notes,
            "executed_at": a.executed_at.isoformat() if a.executed_at else None,
        }

    def _prompt_to_dict(self, t: PromptTemplate) -> dict:
        return {
            "template_id": t.template_id,
            "agent_type": t.agent_type,
            "version": t.version,
            "name": t.name,
            "system_prompt": t.system_prompt,
            "user_prompt_template": t.user_prompt_template,
            "is_active": t.is_active,
            "change_notes": t.change_notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import Integer, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decision import Decision
from app.models.lesson import Lesson
from app.repositories.decision_repo import DecisionRepository
from app.repositories.lesson_repo import LessonRepository
from app.services.embedding_service import embedding_service
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class ExperienceService:
    def __init__(
        self,
        session: AsyncSession,
        memory: MemoryService | None = None,
    ):
        self.session = session
        self.memory = memory
        self.decision_repo = DecisionRepository(session)
        self.lesson_repo = LessonRepository(session)
        self._feedback_scores: dict[str, float] = {}

    async def record_feedback(
        self,
        entity_type: str,
        entity_id: str,
        score: float,
        comment: str = "",
    ) -> None:
        key = f"{entity_type}_{entity_id}"
        self._feedback_scores[key] = score
        if self.memory:
            content = f"Feedback: {score}/5.0 - {comment}"
            await self.memory.index_entity(
                entity_type=f"feedback_{entity_type}",
                entity_id=entity_id,
                project_id="",
                content=content,
            )
        logger.info("Feedback recorded for %s: %.1f/5.0", key, score)

    async def get_weighted_experiences(
        self,
        project_id: str,
        query: str,
        entity_type: str | None = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[dict]:
        if not self.memory:
            return []

        results = []
        for page in range(3):
            batch = await self.memory.query(
                project_id=project_id,
                query=query,
                filter_types=[entity_type] if entity_type else None,
                limit=limit,
            )
            results.extend(batch)
            if len(batch) < limit:
                break

        scored = []
        for r in results:
            eid = r.get("entity_id", "")
            etype = r.get("entity_type", "")
            key = f"{etype}_{eid}"
            feedback_score = self._feedback_scores.get(key, 0.0)
            weight = 0.7 * r.get("score", 0) + 0.3 * (feedback_score / 5.0)
            r["feedback_score"] = feedback_score
            r["weighted_score"] = round(weight, 4)
            if weight >= min_score:
                scored.append(r)

        scored.sort(key=lambda x: x["weighted_score"], reverse=True)
        return scored[:limit]

    async def get_top_lessons(
        self,
        project_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        return await self.get_weighted_experiences(
            project_id=project_id,
            query=query,
            entity_type="lesson",
            limit=limit,
        )

    async def get_top_decisions(
        self,
        project_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        return await self.get_weighted_experiences(
            project_id=project_id,
            query=query,
            entity_type="decision",
            limit=limit,
        )

    async def get_project_stats(self, project_id: str) -> dict:
        decision_count = 0
        lesson_count = 0
        try:
            dec_result = await self.session.execute(
                select(func.count(Decision.decision_id)).where(Decision.project_id == project_id)
            )
            decision_count = dec_result.scalar() or 0
            les_result = await self.session.execute(
                select(func.count(Lesson.lesson_id)).where(Lesson.project_id == project_id)
            )
            lesson_count = les_result.scalar() or 0
        except Exception as exc:
            logger.warning("Could not fetch experience stats: %s", exc)

        feedback_keys = [k for k in self._feedback_scores if k.endswith(f"_{project_id}") or True]
        relevant_feedbacks = {
            k: v for k, v in self._feedback_scores.items()
            if k.startswith("lesson_") or k.startswith("decision_")
        }
        avg_score = sum(relevant_feedbacks.values()) / len(relevant_feedbacks) if relevant_feedbacks else 0.0

        return {
            "project_id": project_id,
            "total_decisions": decision_count,
            "total_lessons": lesson_count,
            "total_feedbacks": len(relevant_feedbacks),
            "average_feedback_score": round(avg_score, 2),
        }

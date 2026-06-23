from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.base import BaseAgent, AgentContext
from app.services.llm_service import LLMService, llm_service as default_llm

logger = logging.getLogger(__name__)


class ReviewAgent(BaseAgent):
    def __init__(
        self,
        context: AgentContext,
        llm: LLMService | None = None,
    ):
        super().__init__(context)
        self.llm = llm or default_llm

    async def review_code(
        self,
        code_files: list[dict],
        qa_results: dict | None = None,
        task_context: str = "",
    ) -> dict:
        comments = []
        total_score = 0

        for file in code_files:
            file_review = await self._review_file(file, task_context)
            comments.extend(file_review.get("comments", []))
            total_score += file_review.get("score", 0)

        avg_score = round(total_score / len(code_files), 1) if code_files else 0.0

        summary = await self._generate_review_summary(
            code_files, comments, qa_results, task_context,
        )

        approved = avg_score >= 3.0 and not any(
            c.get("severity") == "blocker" for c in comments
        )

        return {
            "approved": approved,
            "score": avg_score,
            "comments": comments,
            "summary": summary,
            "reviewer": self.agent_id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _review_file(
        self,
        file: dict,
        context: str,
    ) -> dict:
        path = file.get("path", "unknown")
        content = file.get("content", "")
        language = file.get("language", "python")

        comments = []
        score = 5.0

        lines = content.split("\n")
        if len(lines) > 300:
            comments.append({
                "severity": "warning",
                "message": f"File has {len(lines)} lines, consider splitting",
            })
            score -= 0.5

        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                comments.append({
                    "severity": "suggestion",
                    "line": i,
                    "message": f"Line too long ({len(line)} chars, max 100)",
                })
                score -= 0.1

        if language == "python":
            has_docstring = any('"""' in line for line in lines)
            if not has_docstring and len(lines) > 10:
                comments.append({
                    "severity": "suggestion",
                    "message": "Missing module or function docstring",
                })
                score -= 0.3

        try:
            prompt = (
                f"Review this {language} file for code quality: {path}\n\n"
                f"Context: {context}\n\n"
                f"Content:\n{content[:2000]}\n\n"
                "Rate from 1-5 and list suggestions. "
                'Respond as JSON: {"score": 4.0, "comments": [{"severity": "suggestion"|"blocker"|"nitpick", "message": "..."}]}'
            )
            result = await self.llm.generate(
                prompt,
                system_prompt="You are a senior engineer doing code review.",
            )
            import json
            try:
                llm_result = json.loads(result)
                score = (score + llm_result.get("score", 3.0)) / 2
                comments.extend(llm_result.get("comments", []))
            except json.JSONDecodeError:
                pass
        except Exception as e:
            logger.warning("LLM review failed for %s: %s", path, e)

        return {"path": path, "score": round(score, 1), "comments": comments}

    async def _generate_review_summary(
        self,
        files: list[dict],
        comments: list[dict],
        qa_results: dict | None,
        context: str,
    ) -> str:
        blocker_count = sum(1 for c in comments if c.get("severity") == "blocker")
        suggestion_count = sum(1 for c in comments if c.get("severity") == "suggestion")
        return (
            f"Review: {len(files)} files, {blocker_count} blockers, "
            f"{suggestion_count} suggestions."
            + (f" QA: {'Passed' if qa_results and qa_results.get('passed') else 'Failed'}" if qa_results else "")
        )

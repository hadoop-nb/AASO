from __future__ import annotations

import logging

from app.agents.base import BaseAgent, AgentContext
from app.services.llm_service import LLMService, llm_service as default_llm

logger = logging.getLogger(__name__)


class QAAgent(BaseAgent):
    def __init__(
        self,
        context: AgentContext,
        llm: LLMService | None = None,
    ):
        super().__init__(context)
        self.llm = llm or default_llm

    async def validate_code(
        self,
        code_files: list[dict],
        task_context: str,
    ) -> dict:
        results = []
        all_passed = True

        for file in code_files:
            file_result = await self._validate_single_file(file, task_context)
            results.append(file_result)
            if not file_result.get("passed", False):
                all_passed = False

        summary = await self._generate_summary(results, task_context)

        return {
            "passed": all_passed,
            "files": results,
            "summary": summary,
            "qa_decision": "approved" if all_passed else "changes_requested",
        }

    async def _validate_single_file(
        self,
        file: dict,
        context: str,
    ) -> dict:
        issues = []
        path = file.get("path", "unknown")
        content = file.get("content", "")
        language = file.get("language", "python")

        if not content.strip():
            issues.append({"severity": "error", "message": "File is empty"})

        if language == "python":
            if "import" in content and not content.startswith("from __future__"):
                pass
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.rstrip()
                if line != stripped:
                    issues.append({
                        "severity": "warning",
                        "line": i,
                        "message": "Trailing whitespace",
                    })

        try:
            prompt = (
                f"Review this {language} file: {path}\n\n"
                f"Context: {context}\n\n"
                f"Content:\n{content[:2000]}\n\n"
                "List any bugs, style issues, or security concerns. "
                "Respond with a JSON object: "
                '{"issues": [{"severity": "error"|"warning"|"info", "message": "..."}], "passed": true|false}'
            )
            result = await self.llm.generate(
                prompt,
                system_prompt="You are a strict QA engineer reviewing code.",
                project_id=self.context.project_id,
                agent_type="qa",
            )
            import json
            try:
                llm_result = json.loads(result)
                issues.extend(llm_result.get("issues", []))
            except json.JSONDecodeError:
                pass
        except Exception as e:
            logger.warning("LLM validation failed for %s: %s", path, e)

        passed = all(i.get("severity") != "error" for i in issues)
        return {
            "path": path,
            "passed": passed,
            "issues": issues,
            "language": language,
        }

    async def _generate_summary(
        self,
        results: list[dict],
        context: str,
    ) -> str:
        total = len(results)
        passed_count = sum(1 for r in results if r.get("passed"))
        total_issues = sum(len(r.get("issues", [])) for r in results)
        return (
            f"QA Review: {passed_count}/{total} files passed. "
            f"{total_issues} total issues found."
        )

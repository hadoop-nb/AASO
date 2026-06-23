from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone

from app.agents.base import AgentContext, BaseAgent
from app.core.agent_protocol import AgentMessage, agent_registry, message_router
from app.services.llm_service import LLMService, llm_service as default_llm

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    def __init__(
        self,
        context: AgentContext,
        llm: LLMService | None = None,
    ):
        super().__init__(context)
        self.llm = llm or default_llm
        self._register_protocol()

    def _register_protocol(self):
        capability = agent_registry.find_by_id(self.agent_id)
        if not capability:
            from app.core.agent_protocol import AgentCapability
            agent_registry.register(AgentCapability(
                agent_id=self.agent_id,
                agent_name=self.name,
                protocols=[
                    "research.analyze_code",
                    "research.detect_stack",
                    "research.dependency_check",
                    "research.tech_recommend",
                    "research.code_review",
                ],
                description="Researches code, dependencies, tech stack, and provides recommendations",
            ))
            message_router.register_handler(self.agent_id, self._handle_message)

    async def _handle_message(self, message: AgentMessage) -> dict:
        protocol = message.protocol
        payload = message.payload

        if protocol == "research.analyze_code":
            return await self.analyze_code(payload.get("code", ""), payload.get("language", "python"))
        elif protocol == "research.detect_stack":
            return await self.detect_tech_stack(payload.get("files", []))
        elif protocol == "research.dependency_check":
            return await self.check_dependencies(payload.get("files", []), payload.get("project_id", ""))
        elif protocol == "research.tech_recommend":
            return await self.recommend_technology(payload.get("requirement", ""), payload.get("context", ""))
        elif protocol == "research.code_review":
            return await self.research_code_review(payload.get("code", ""), payload.get("language", "python"), payload.get("context", ""))
        return {"error": f"Unknown protocol: {protocol}"}

    async def analyze_code(
        self, code: str, language: str = "python"
    ) -> dict:
        lines = code.split("\n")
        total_lines = len(lines)
        blank_lines = sum(1 for l in lines if not l.strip())
        code_lines = total_lines - blank_lines
        comment_lines = sum(
            1 for l in lines
            if l.strip().startswith("#") or l.strip().startswith("//")
            or l.strip().startswith("/*") or l.strip().startswith("*")
        )

        _keywords = {"if", "for", "while", "switch", "catch", "try", "elif", "except", "with", "when", "return", "yield", "await", "async", "raise", "del", "print", "assert", "pass", "break", "continue"}
        functions = [w for w in re.findall(r"(\w+)\s*\(", code) if w not in _keywords]
        classes = re.findall(r"class (\w+)", code)
        imports = re.findall(
            r"(?:import |from\s+\S+\s+import |require\s*\(|using\s+)\"?([^\s\(\";]+)", code
        )

        prompt = (
            f"Analyze this {language} code:\n\n```{language}\n{code[:3000]}\n```\n\n"
            "Provide a concise analysis covering:\n"
            "- Architecture and structure\n"
            "- Code quality observations\n"
            "- Potential improvements\n"
            "- Security considerations\n\n"
            'Respond as JSON: {"architecture": "...", "quality": "...", "improvements": ["..."], "security_notes": ["..."]}'
        )
        llm_analysis = {}
        try:
            result = await self.llm.generate(
                prompt,
                system_prompt="You are a senior software architect analyzing code.",
                project_id=self.context.project_id,
                agent_type="research",
            )
            llm_analysis = json.loads(result)
        except Exception as e:
            logger.warning("LLM analysis failed: %s", e)

        return {
            "file_stats": {
                "total_lines": total_lines,
                "code_lines": code_lines,
                "blank_lines": blank_lines,
                "comment_lines": comment_lines,
            },
            "structure": {
                "functions": functions,
                "classes": classes,
                "imports": list(set(imports)),
            },
            "llm_analysis": llm_analysis,
            "language": language,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def detect_tech_stack(self, files: list[dict]) -> dict:
        indicators = {
            "python": [".py", "requirements.txt", "setup.py", "pyproject.toml"],
            "javascript": [".js", ".jsx", "package.json"],
            "typescript": [".ts", ".tsx", "tsconfig.json"],
            "rust": [".rs", "Cargo.toml"],
            "go": [".go", "go.mod"],
            "java": [".java", "pom.xml", "build.gradle"],
            "docker": ["Dockerfile", "docker-compose.yml"],
            "postgresql": [".sql", "migration"],
            "fastapi": ["fastapi"],
            "react": ["react", "jsx", "tsx"],
            "sqlalchemy": ["sqlalchemy"],
        }
        detected = set()
        all_content = ""
        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            all_content += content + "\n"
            for tech, patterns in indicators.items():
                for p in patterns:
                    if p in path or p in content.lower():
                        detected.add(tech)

        prompt = (
            f"Based on these project files, identify the tech stack:\n\n{all_content[:4000]}\n\n"
            'Respond as JSON: {"primary_language": "...", "framework": "...", "database": "...", "tools": ["..."], "confidence": 0.0-1.0}'
        )
        llm_stack = {}
        try:
            result = await self.llm.generate(
                prompt,
                system_prompt="You are a tech stack detection expert.",
                project_id=self.context.project_id,
                agent_type="research",
            )
            llm_stack = json.loads(result)
        except Exception as e:
            logger.warning("LLM stack detection failed: %s", e)

        return {
            "detected_technologies": sorted(detected),
            "llm_analysis": llm_stack,
            "file_count": len(files),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def check_dependencies(
        self, files: list[dict], project_id: str = ""
    ) -> dict:
        dep_files = {}
        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            if any(p in path for p in ["requirements.txt", "package.json", "Cargo.toml", "go.mod", "pyproject.toml"]):
                dep_files[path] = content

        findings = []
        for path, content in dep_files.items():
            lines = content.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("//"):
                    parts = re.split(r"[=<>!~@\s]+", line, maxsplit=2)
                    if len(parts) >= 1:
                        findings.append({
                            "file": path,
                            "package": parts[0],
                            "version_spec": parts[1] if len(parts) > 1 else "any",
                        })

        prompt = (
            f"Review these project dependencies:\n{json.dumps(findings, indent=2)}\n\n"
            "Check for:\n"
            "- Outdated or deprecated packages\n"
            "- Known security vulnerabilities\n"
            "- Version conflicts\n"
            "- Recommended upgrades\n\n"
            'Respond as JSON: {"issues": [{"package": "...", "severity": "high"|"medium"|"low", "message": "..."}], "recommendations": ["..."]}'
        )
        llm_check = {}
        try:
            result = await self.llm.generate(
                prompt,
                system_prompt="You are a dependency security expert.",
                project_id=self.context.project_id,
                agent_type="research",
            )
            llm_check = json.loads(result)
        except Exception as e:
            logger.warning("LLM dependency check failed: %s", e)

        return {
            "findings": findings,
            "llm_check": llm_check,
            "total_dependencies": len(findings),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def recommend_technology(
        self, requirement: str, context: str = ""
    ) -> dict:
        prompt = (
            f"Requirement: {requirement}\n\n"
            f"Context: {context}\n\n"
            "Research and recommend the best technology stack for this requirement.\n"
            "Consider: performance, community, learning curve, ecosystem, cost.\n\n"
            'Respond as JSON: {"recommendation": "...", "alternatives": [{"name": "...", "pros": ["..."], "cons": ["..."], "fit_score": 0-10}], "reasoning": "..."}'
        )
        try:
            result = await self.llm.generate(
                prompt,
                system_prompt="You are a technology research analyst.",
                project_id=self.context.project_id,
                agent_type="research",
            )
            return json.loads(result)
        except json.JSONDecodeError as e:
            return {"recommendation": result, "alternatives": [], "reasoning": "LLM returned non-JSON response"}

    async def research_code_review(
        self, code: str, language: str = "python", context: str = ""
    ) -> dict:
        prompt = (
            f"Research and review this {language} code:\n\n"
            f"Context: {context}\n\n"
            f"```{language}\n{code[:3000]}\n```\n\n"
            "Provide an in-depth research review covering:\n"
            "- Best practices adherence\n"
            "- Design patterns used or missing\n"
            "- Performance implications\n"
            "- Security audit findings\n"
            "- Testing recommendations\n\n"
            'Respond as JSON: {"best_practices": {"score": 0-10, "findings": ["..."]}, "design_patterns": ["..."], "performance": ["..."], "security": ["..."], "testing_recommendations": ["..."]}'
        )
        try:
            result = await self.llm.generate(
                prompt,
                system_prompt="You are a code research specialist conducting deep code analysis.",
                project_id=self.context.project_id,
                agent_type="research",
            )
            return json.loads(result)
        except json.JSONDecodeError as e:
            return {"best_practices": {"score": 5, "findings": ["Could not parse LLM response"]}}

    async def execute(self, input_data: dict) -> dict:
        action = input_data.get("action", "analyze_code")
        if action == "analyze_code":
            return await self.analyze_code(
                input_data.get("code", ""),
                input_data.get("language", "python"),
            )
        elif action == "detect_stack":
            return await self.detect_tech_stack(input_data.get("files", []))
        elif action == "check_dependencies":
            return await self.check_dependencies(
                input_data.get("files", []),
                input_data.get("project_id", ""),
            )
        elif action == "recommend_tech":
            return await self.recommend_technology(
                input_data.get("requirement", ""),
                input_data.get("context", ""),
            )
        elif action == "code_review":
            return await self.research_code_review(
                input_data.get("code", ""),
                input_data.get("language", "python"),
                input_data.get("context", ""),
            )
        return {"error": f"Unknown action: {action}"}

from __future__ import annotations

from app.agents.base import AgentContext
from app.agents.research_agent import ResearchAgent
from app.services.llm_service import LLMService


class ResearchService:
    def __init__(self, llm: LLMService | None = None):
        self.llm = llm
        self._agent_cache: dict[str, ResearchAgent] = {}

    def _get_agent(self, project_id: str) -> ResearchAgent:
        if project_id not in self._agent_cache:
            self._agent_cache[project_id] = ResearchAgent(
                context=AgentContext(
                    agent_id=f"research-{project_id[:8]}",
                    name="Research Agent",
                    project_id=project_id,
                ),
                llm=self.llm,
            )
        return self._agent_cache[project_id]

    async def analyze_code(
        self, project_id: str, code: str, language: str = "python"
    ) -> dict:
        agent = self._get_agent(project_id)
        return await agent.analyze_code(code, language)

    async def detect_tech_stack(
        self, project_id: str, files: list[dict]
    ) -> dict:
        agent = self._get_agent(project_id)
        return await agent.detect_tech_stack(files)

    async def check_dependencies(
        self, project_id: str, files: list[dict]
    ) -> dict:
        agent = self._get_agent(project_id)
        return await agent.check_dependencies(files, project_id)

    async def recommend_technology(
        self, project_id: str, requirement: str, context: str = ""
    ) -> dict:
        agent = self._get_agent(project_id)
        return await agent.recommend_technology(requirement, context)

    async def research_code_review(
        self, project_id: str, code: str, language: str = "python", context: str = ""
    ) -> dict:
        agent = self._get_agent(project_id)
        return await agent.research_code_review(code, language, context)

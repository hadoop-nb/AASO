from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.orchestrator import OrchestratorAgent, OrchestrationRun
from app.services.analytics_service import AnalyticsService
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService


class OrchestratorService:
    def __init__(
        self,
        session: AsyncSession,
        llm: LLMService | None = None,
        memory: MemoryService | None = None,
    ):
        self.session = session
        self.llm = llm
        self.memory = memory
        self.analytics = AnalyticsService(session)

    async def orchestrate(
        self,
        project_id: str,
        goal: str,
        run_id: str | None = None,
    ) -> dict:
        agent = OrchestratorAgent(
            context=AgentContext(
                agent_id="orchestrator-001",
                name="Orchestrator Agent",
                project_id=project_id,
            ),
            session=self.session,
            llm=self.llm,
            memory=self.memory,
            analytics=self.analytics,
        )
        input_data = {"project_id": project_id, "goal": goal}
        if run_id:
            input_data["run_id"] = run_id
        return await agent.execute(input_data)

    async def get_run(
        self, project_id: str, run_id: str
    ) -> OrchestrationRun | None:
        agent = OrchestratorAgent(
            context=AgentContext(
                agent_id="orchestrator-001",
                name="Orchestrator Agent",
                project_id=project_id,
            ),
            session=self.session,
            llm=self.llm,
            memory=self.memory,
        )
        return agent.get_run(run_id)

    async def list_runs(
        self, project_id: str
    ) -> list[OrchestrationRun]:
        agent = OrchestratorAgent(
            context=AgentContext(
                agent_id="orchestrator-001",
                name="Orchestrator Agent",
                project_id=project_id,
            ),
            session=self.session,
            llm=self.llm,
            memory=self.memory,
        )
        return agent.list_runs(project_id)

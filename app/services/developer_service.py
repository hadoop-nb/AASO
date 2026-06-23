from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.developer import DeveloperAgent
from app.services.memory_service import MemoryService


class DeveloperService:
    def __init__(
        self,
        session: AsyncSession,
        memory: MemoryService | None = None,
    ):
        self.session = session
        self.memory = memory

    async def execute_task(
        self, project_id: str, task_id: str
    ) -> dict:
        agent = DeveloperAgent(
            context=AgentContext(
                agent_id="dev-001",
                name="Developer Agent",
                project_id=project_id,
                task_id=task_id,
            ),
            session=self.session,
            memory=self.memory,
        )
        return await agent.execute(
            {"task_id": task_id, "project_id": project_id}
        )

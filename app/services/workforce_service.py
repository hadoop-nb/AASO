from __future__ import annotations

import logging

from app.core.agent_pool import AgentPool, AgentStatus, PooledAgent, agent_pool as default_pool

logger = logging.getLogger(__name__)


class WorkforceService:
    def __init__(self, pool: AgentPool | None = None):
        self._pool = pool or default_pool

    def register_agent(
        self,
        agent_type: str,
        agent_id: str | None = None,
        metadata: dict | None = None,
    ) -> PooledAgent:
        return self._pool.register(agent_type, agent_id, metadata)

    def unregister_agent(self, agent_id: str) -> bool:
        return self._pool.unregister(agent_id)

    def acquire_agent(
        self,
        agent_type: str,
        task_id: str | None = None,
        project_id: str | None = None,
    ) -> PooledAgent | None:
        return self._pool.acquire(agent_type, task_id, project_id)

    def release_agent(self, agent_id: str, error: bool = False) -> bool:
        return self._pool.release(agent_id, error)

    def get_agent(self, agent_id: str) -> PooledAgent | None:
        return self._pool.get_agent(agent_id)

    def list_agents(
        self,
        agent_type: str | None = None,
        status: AgentStatus | None = None,
    ) -> list[dict]:
        agents = self._pool.list_agents(agent_type, status)
        return [
            {
                "agent_id": a.agent_id,
                "agent_type": a.agent_type,
                "status": a.status.value,
                "current_task_id": a.current_task_id,
                "current_project_id": a.current_project_id,
                "completed_tasks": a.completed_tasks,
                "error_count": a.error_count,
                "is_available": a.is_available,
            }
            for a in agents
        ]

    def get_pool_summary(self) -> dict:
        summary = self._pool.get_pool_summary()
        details = self.list_agents()
        summary["agents"] = details
        return summary

    def auto_register_standard_agents(self):
        """Register one instance of each standard agent type."""
        for agent_type in ["developer", "qa", "review", "research", "orchestrator"]:
            self.register_agent(
                agent_type,
                f"{agent_type}-001",
                {"auto_registered": True},
            )


workforce_service = WorkforceService()

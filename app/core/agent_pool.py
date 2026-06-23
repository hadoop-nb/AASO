from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class PooledAgent:
    agent_id: str
    agent_type: str
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: str | None = None
    current_project_id: str | None = None
    started_at: datetime | None = None
    completed_tasks: int = 0
    error_count: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.status == AgentStatus.IDLE

    @property
    def busy_duration_seconds(self) -> float:
        if self.status == AgentStatus.BUSY and self.started_at:
            return (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return 0.0


class AgentPool:
    def __init__(self):
        self._agents: dict[str, PooledAgent] = {}
        self._agent_types: dict[str, list[str]] = {}

    def register(
        self,
        agent_type: str,
        agent_id: str | None = None,
        metadata: dict | None = None,
    ) -> PooledAgent:
        if agent_id and agent_id in self._agents:
            agent = self._agents[agent_id]
            agent.agent_type = agent_type
            agent.metadata = metadata or {}
            return agent

        agent = PooledAgent(
            agent_id=agent_id or f"{agent_type}-{int(time.time())}",
            agent_type=agent_type,
            metadata=metadata or {},
        )
        self._agents[agent.agent_id] = agent
        self._agent_types.setdefault(agent_type, []).append(agent.agent_id)
        logger.info(
            "Registered agent %s of type %s", agent.agent_id, agent_type
        )
        return agent

    def unregister(self, agent_id: str) -> bool:
        agent = self._agents.pop(agent_id, None)
        if agent:
            type_list = self._agent_types.get(agent.agent_type, [])
            if agent_id in type_list:
                type_list.remove(agent_id)
            return True
        return False

    def acquire(
        self,
        agent_type: str,
        task_id: str | None = None,
        project_id: str | None = None,
    ) -> PooledAgent | None:
        type_list = self._agent_types.get(agent_type, [])
        for agent_id in type_list:
            agent = self._agents.get(agent_id)
            if agent and agent.is_available:
                agent.status = AgentStatus.BUSY
                agent.current_task_id = task_id
                agent.current_project_id = project_id
                agent.started_at = datetime.now(timezone.utc)
                logger.info(
                    "Acquired agent %s for task %s", agent_id, task_id
                )
                return agent
        return None

    def release(self, agent_id: str, error: bool = False) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.status = AgentStatus.IDLE
        agent.current_task_id = None
        agent.current_project_id = None
        agent.started_at = None
        if error:
            agent.error_count += 1
        else:
            agent.completed_tasks += 1
        logger.info("Released agent %s", agent_id)
        return True

    def mark_error(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.status = AgentStatus.ERROR
        agent.error_count += 1
        return True

    def get_agent(self, agent_id: str) -> PooledAgent | None:
        return self._agents.get(agent_id)

    def list_agents(
        self,
        agent_type: str | None = None,
        status: AgentStatus | None = None,
    ) -> list[PooledAgent]:
        agents = list(self._agents.values())
        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        if status:
            agents = [a for a in agents if a.status == status]
        return sorted(agents, key=lambda a: a.agent_id)

    def count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for agent in self._agents.values():
            counts[agent.agent_type] = counts.get(agent.agent_type, 0) + 1
        return counts

    def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for agent in self._agents.values():
            s = agent.status.value
            counts[s] = counts.get(s, 0) + 1
        return counts

    def get_pool_summary(self) -> dict:
        return {
            "total_agents": len(self._agents),
            "by_type": self.count_by_type(),
            "by_status": self.count_by_status(),
            "available": sum(1 for a in self._agents.values() if a.is_available),
            "busy": sum(1 for a in self._agents.values() if a.status == AgentStatus.BUSY),
        }


agent_pool = AgentPool()

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentContext:
    agent_id: str
    name: str
    project_id: str
    task_id: str | None = None
    config: dict = field(default_factory=dict)


class BaseAgent:
    def __init__(self, context: AgentContext) -> None:
        self.context = context
        self.agent_id = context.agent_id
        self.name = context.name

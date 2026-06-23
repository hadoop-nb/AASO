from __future__ import annotations

from dataclasses import dataclass, field

from app.core.agent_protocol import (
    AgentCapability,
    AgentMessage,
    agent_registry,
    message_router,
)


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

    async def send_message(self, message: AgentMessage) -> None:
        await message_router.send_message(message)

    async def request(
        self,
        target_agent: str,
        protocol: str,
        payload: dict,
        timeout: float = 30.0,
    ) -> dict:
        return await message_router.request(
            target_agent=target_agent,
            protocol=protocol,
            payload=payload,
            source_agent=self.agent_id,
            timeout=timeout,
        )

    def register_in_protocol(
        self,
        protocols: list[str],
        description: str = "",
    ) -> None:
        cap = AgentCapability(
            agent_id=self.agent_id,
            agent_name=self.name,
            protocols=protocols,
            description=description or f"{self.name} agent",
        )
        agent_registry.register(cap)

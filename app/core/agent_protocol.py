from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.core.event_bus import Event, event_bus

logger = logging.getLogger(__name__)

MessageHandler = Callable[["AgentMessage"], Awaitable[dict]]


class MessageStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass
class AgentMessage:
    message_id: str
    protocol: str
    payload: dict
    source_agent: str
    target_agent: str = "*"
    correlation_id: str | None = None
    response_to: str | None = None
    status: MessageStatus = MessageStatus.PENDING
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConversationThread:
    thread_id: str
    protocol: str
    participants: list[str]
    messages: list[AgentMessage] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict = field(default_factory=dict)
    status: str = "active"


@dataclass
class WorkspaceEntry:
    key: str
    value: dict
    created_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: float | None = None


class SharedWorkspace:
    def __init__(self):
        self._entries: dict[str, WorkspaceEntry] = {}

    def set(self, key: str, value: dict, created_by: str, ttl: float | None = None) -> None:
        self._entries[key] = WorkspaceEntry(
            key=key, value=value, created_by=created_by, ttl_seconds=ttl,
        )
        self._expire_old()

    def get(self, key: str) -> dict | None:
        self._expire_old()
        entry = self._entries.get(key)
        if entry:
            return entry.value
        return None

    def delete(self, key: str) -> bool:
        return self._entries.pop(key, None) is not None

    def list_keys(self) -> list[str]:
        self._expire_old()
        return list(self._entries.keys())

    def clear(self) -> None:
        self._entries.clear()

    def _expire_old(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [
            k for k, v in self._entries.items()
            if v.ttl_seconds is not None
            and (now - v.created_at).total_seconds() > v.ttl_seconds
        ]
        for k in expired:
            del self._entries[k]

    def to_dict(self) -> dict:
        self._expire_old()
        return {
            k: {
                "key": v.key,
                "value": v.value,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat(),
            }
            for k, v in self._entries.items()
        }


@dataclass
class AgentCapability:
    agent_id: str
    agent_name: str
    protocols: list[str]
    description: str = ""


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentCapability] = {}

    def register(self, capability: AgentCapability) -> None:
        self._agents[capability.agent_id] = capability
        logger.info(
            "Registered agent %s with protocols: %s",
            capability.agent_id,
            capability.protocols,
        )

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def find_by_protocol(self, protocol: str) -> list[AgentCapability]:
        return [a for a in self._agents.values() if protocol in a.protocols]

    def find_by_id(self, agent_id: str) -> AgentCapability | None:
        return self._agents.get(agent_id)

    def list_all(self) -> list[AgentCapability]:
        return list(self._agents.values())

    def clear(self) -> None:
        self._agents.clear()


agent_registry = AgentRegistry()


class MessageRouter:
    def __init__(self):
        self._handlers: dict[str, MessageHandler] = {}
        self._pending_responses: dict[str, asyncio.Future] = {}
        self._history: list[AgentMessage] = []
        self._max_history = 200
        self._subscribed = False
        self._threads: dict[str, ConversationThread] = {}
        self._workspace = SharedWorkspace()

    async def _on_agent_message(self, event: Event) -> None:
        if event.event_type != "agent_protocol:message":
            return
        msg_data = event.data
        message = AgentMessage(
            message_id=msg_data["message_id"],
            protocol=msg_data["protocol"],
            payload=msg_data["payload"],
            source_agent=msg_data["source_agent"],
            target_agent=msg_data.get("target_agent", "*"),
            correlation_id=msg_data.get("correlation_id"),
            response_to=msg_data.get("response_to"),
        )
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        thread_id = msg_data.get("thread_id")
        if thread_id and thread_id in self._threads:
            self._threads[thread_id].messages.append(message)

        if message.response_to:
            future = self._pending_responses.pop(message.response_to, None)
            if future:
                future.set_result(message)
            return

        asyncio.create_task(self._dispatch_message(message))

    async def _dispatch_message(self, message: AgentMessage) -> None:
        if message.target_agent != "*":
            handler = self._handlers.get(message.target_agent)
            if handler:
                await self._run_handler(handler, message, message.target_agent)
            else:
                await self._dispatch_by_protocol(message)
        else:
            await self._dispatch_by_protocol(message)

    async def _dispatch_by_protocol(self, message: AgentMessage) -> None:
        candidates = agent_registry.find_by_protocol(message.protocol)
        for cap in candidates:
            handler = self._handlers.get(cap.agent_id)
            if handler:
                asyncio.create_task(self._run_handler(handler, message, cap.agent_id))

    async def _run_handler(
        self, handler: MessageHandler, message: AgentMessage, agent_id: str
    ) -> None:
        try:
            result = await handler(message)
            if message.correlation_id:
                response = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    protocol=message.protocol,
                    payload=result,
                    source_agent=agent_id,
                    target_agent=message.source_agent,
                    response_to=message.correlation_id,
                )
                await self.send_message(response)
        except Exception as e:
            logger.error("Handler %s failed: %s", agent_id, e)
            if message.correlation_id:
                error_response = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    protocol=message.protocol,
                    payload={"error": str(e)},
                    source_agent=agent_id,
                    target_agent=message.source_agent,
                    response_to=message.correlation_id,
                )
                await self.send_message(error_response)

    def register_handler(self, agent_id: str, handler: MessageHandler) -> None:
        self._handlers[agent_id] = handler
        logger.info("Registered message handler for agent: %s", agent_id)

    def unregister_handler(self, agent_id: str) -> None:
        self._handlers.pop(agent_id, None)

    def _ensure_subscribed(self):
        if not self._subscribed:
            event_bus.subscribe("agent_protocol:message", self._on_agent_message)
            self._subscribed = True

    async def send_message(self, message: AgentMessage) -> None:
        self._ensure_subscribed()
        message.status = MessageStatus.DELIVERED
        await event_bus.publish(Event(
            event_type="agent_protocol:message",
            source="message_router",
            data={
                "message_id": message.message_id,
                "protocol": message.protocol,
                "payload": message.payload,
                "source_agent": message.source_agent,
                "target_agent": message.target_agent,
                "correlation_id": message.correlation_id,
                "response_to": message.response_to,
            },
        ))

    async def request(
        self,
        target_agent: str,
        protocol: str,
        payload: dict,
        source_agent: str = "system",
        timeout: float = 30.0,
    ) -> dict:
        import asyncio
        correlation_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.Future()
        self._pending_responses[correlation_id] = future

        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            protocol=protocol,
            payload=payload,
            source_agent=source_agent,
            target_agent=target_agent,
            correlation_id=correlation_id,
        )
        await self.send_message(message)

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response.payload
        except asyncio.TimeoutError:
            self._pending_responses.pop(correlation_id, None)
            return {"error": f"Request to {target_agent} timed out after {timeout}s"}

    def get_history(
        self,
        protocol: str | None = None,
        agent_id: str | None = None,
        limit: int = 20,
    ) -> list[AgentMessage]:
        messages = self._history
        if protocol:
            messages = [m for m in messages if m.protocol == protocol]
        if agent_id:
            messages = [
                m for m in messages
                if m.source_agent == agent_id or m.target_agent == agent_id
            ]
        return messages[-limit:]

    def clear(self) -> None:
        self._history.clear()
        self._pending_responses.clear()
        self._threads.clear()
        self._workspace.clear()

    def create_thread(
        self, protocol: str, participants: list[str], context: dict | None = None
    ) -> ConversationThread:
        thread = ConversationThread(
            thread_id=str(uuid.uuid4()),
            protocol=protocol,
            participants=participants,
            context=context or {},
        )
        self._threads[thread.thread_id] = thread
        return thread

    def get_thread(self, thread_id: str) -> ConversationThread | None:
        return self._threads.get(thread_id)

    def list_threads(
        self, protocol: str | None = None, status: str | None = None
    ) -> list[ConversationThread]:
        threads = list(self._threads.values())
        if protocol:
            threads = [t for t in threads if t.protocol == protocol]
        if status:
            threads = [t for t in threads if t.status == status]
        return sorted(threads, key=lambda t: t.started_at, reverse=True)

    def close_thread(self, thread_id: str) -> bool:
        thread = self._threads.get(thread_id)
        if thread:
            thread.status = "closed"
            return True
        return False

    async def send_to_thread(
        self, thread_id: str, message: AgentMessage
    ) -> None:
        thread = self._threads.get(thread_id)
        if thread:
            thread.messages.append(message)
        await self.send_message(message)

    async def delegate(
        self,
        target_agent: str,
        protocol: str,
        task: dict,
        source_agent: str = "system",
        timeout: float = 60.0,
        thread_id: str | None = None,
    ) -> dict:
        import asyncio

        correlation_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.Future()
        self._pending_responses[correlation_id] = future

        payload = {"task": task, "thread_id": thread_id} if thread_id else {"task": task}
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            protocol=protocol,
            payload=payload,
            source_agent=source_agent,
            target_agent=target_agent,
            correlation_id=correlation_id,
        )

        if thread_id and thread_id in self._threads:
            self._threads[thread_id].messages.append(message)

        await self.send_message(message)

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response.payload
        except asyncio.TimeoutError:
            self._pending_responses.pop(correlation_id, None)
            return {"error": f"Delegation to {target_agent} timed out after {timeout}s"}

    def workspace(self) -> SharedWorkspace:
        return self._workspace


message_router = MessageRouter()
shared_workspace = SharedWorkspace()


import asyncio

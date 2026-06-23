from __future__ import annotations

import pytest

from app.core.agent_protocol import (
    AgentCapability,
    AgentMessage,
    MessageStatus,
    agent_registry,
    message_router,
)


@pytest.fixture(autouse=True)
def reset_registry():
    agent_registry.clear()
    message_router.clear()


def test_agent_registry_register_and_find():
    cap = AgentCapability(
        agent_id="test-agent",
        agent_name="Test Agent",
        protocols=["test.protocol", "test.ping"],
        description="Test agent for unit tests",
    )
    agent_registry.register(cap)

    found = agent_registry.find_by_id("test-agent")
    assert found is not None
    assert found.agent_id == "test-agent"

    by_protocol = agent_registry.find_by_protocol("test.ping")
    assert len(by_protocol) == 1
    assert by_protocol[0].agent_id == "test-agent"

    by_unknown = agent_registry.find_by_protocol("nonexistent")
    assert len(by_unknown) == 0


def test_agent_registry_list_and_unregister():
    cap1 = AgentCapability(agent_id="a1", agent_name="Agent 1", protocols=["p1"])
    cap2 = AgentCapability(agent_id="a2", agent_name="Agent 2", protocols=["p2"])
    agent_registry.register(cap1)
    agent_registry.register(cap2)

    all_agents = agent_registry.list_all()
    assert len(all_agents) == 2

    agent_registry.unregister("a1")
    assert agent_registry.find_by_id("a1") is None
    assert len(agent_registry.list_all()) == 1


def test_agent_registry_clear():
    agent_registry.register(
        AgentCapability(agent_id="x", agent_name="X", protocols=["x"])
    )
    agent_registry.clear()
    assert len(agent_registry.list_all()) == 0


def test_agent_message_creation():
    msg = AgentMessage(
        message_id="msg-1",
        protocol="test.analyze",
        payload={"code": "print('hello')"},
        source_agent="agent-a",
        target_agent="agent-b",
        correlation_id="corr-1",
    )
    assert msg.message_id == "msg-1"
    assert msg.protocol == "test.analyze"
    assert msg.payload == {"code": "print('hello')"}
    assert msg.status == MessageStatus.PENDING


@pytest.mark.asyncio
async def test_message_router_send_and_deliver():
    received = []

    async def handler(msg: AgentMessage) -> dict:
        received.append(msg)
        return {"handled": True}

    agent_registry.register(
        AgentCapability(
            agent_id="worker", agent_name="Worker", protocols=["task.work"]
        )
    )
    message_router.register_handler("worker", handler)

    msg = AgentMessage(
        message_id="msg-1",
        protocol="task.work",
        payload={"task": "do_something"},
        source_agent="requester",
        target_agent="worker",
    )
    await message_router.send_message(msg)

    assert len(received) == 1
    assert received[0].message_id == "msg-1"


@pytest.mark.asyncio
async def test_message_router_request_response():
    async def handler(msg: AgentMessage) -> dict:
        return {"result": f"processed {msg.payload.get('item')}"}

    agent_registry.register(
        AgentCapability(
            agent_id="worker2", agent_name="Worker 2", protocols=["task.process"]
        )
    )
    message_router.register_handler("worker2", handler)

    response = await message_router.request(
        target_agent="worker2",
        protocol="task.process",
        payload={"item": "test-item"},
        source_agent="test-suite",
        timeout=5,
    )

    assert response["result"] == "processed test-item"


@pytest.mark.asyncio
async def test_message_router_request_timeout():
    import asyncio

    async def slow_handler(msg: AgentMessage) -> dict:
        await asyncio.sleep(10)
        return {"result": "too late"}

    agent_registry.register(
        AgentCapability(
            agent_id="slow-agent",
            agent_name="Slow Agent",
            protocols=["task.slow"],
        )
    )
    message_router.register_handler("slow-agent", slow_handler)

    response = await message_router.request(
        target_agent="slow-agent",
        protocol="task.slow",
        payload={},
        source_agent="test-suite",
        timeout=0.05,
    )

    assert "error" in response
    assert "timed out" in response["error"]


@pytest.mark.asyncio
async def test_message_router_protocol_broadcast():
    results = []

    async def handler_a(msg: AgentMessage) -> dict:
        results.append(f"a got {msg.payload.get('msg')}")
        return {}

    async def handler_b(msg: AgentMessage) -> dict:
        results.append(f"b got {msg.payload.get('msg')}")
        return {}

    agent_registry.register(
        AgentCapability(
            agent_id="listener-a",
            agent_name="Listener A",
            protocols=["broadcast.test"],
        )
    )
    agent_registry.register(
        AgentCapability(
            agent_id="listener-b",
            agent_name="Listener B",
            protocols=["broadcast.test"],
        )
    )
    message_router.register_handler("listener-a", handler_a)
    message_router.register_handler("listener-b", handler_b)

    msg = AgentMessage(
        message_id="broadcast-1",
        protocol="broadcast.test",
        payload={"msg": "hello everyone"},
        source_agent="broadcaster",
        target_agent="*",
    )
    await message_router.send_message(msg)

    assert len(results) >= 2


def test_message_router_history():
    msg1 = AgentMessage(
        message_id="h-1", protocol="hist.test", payload={},
        source_agent="src", target_agent="dst",
    )
    msg2 = AgentMessage(
        message_id="h-2", protocol="hist.test", payload={},
        source_agent="src", target_agent="dst",
    )

    message_router._history = [msg1, msg2]
    history = message_router.get_history(limit=10)
    assert len(history) == 2

    filtered = message_router.get_history(agent_id="src", limit=10)
    assert len(filtered) >= 1


def test_agent_capability_dataclass():
    cap = AgentCapability(
        agent_id="id-1",
        agent_name="Name",
        protocols=["p1", "p2"],
        description="desc",
    )
    assert cap.agent_id == "id-1"
    assert cap.agent_name == "Name"
    assert cap.protocols == ["p1", "p2"]
    assert cap.description == "desc"


@pytest.mark.asyncio
async def test_base_agent_can_send_messages():
    from app.agents.base import AgentContext, BaseAgent

    received = []
    async def handler(msg: AgentMessage) -> dict:
        received.append(msg)
        return {"ok": True}

    agent_registry.register(
        AgentCapability(
            agent_id="base-target",
            agent_name="Base Target",
            protocols=["base.test"],
        )
    )
    message_router.register_handler("base-target", handler)

    agent = BaseAgent(
        context=AgentContext(
            agent_id="base-sender",
            name="Base Sender",
            project_id="proj-1",
        )
    )

    msg = AgentMessage(
        message_id="base-msg",
        protocol="base.test",
        payload={"data": 42},
        source_agent="base-sender",
        target_agent="base-target",
    )
    await agent.send_message(msg)

    assert len(received) == 1
    assert received[0].payload["data"] == 42


@pytest.mark.asyncio
async def test_base_agent_can_request():
    from app.agents.base import AgentContext, BaseAgent

    async def handler(msg: AgentMessage) -> dict:
        return {"pong": True}

    agent_registry.register(
        AgentCapability(
            agent_id="ping-agent",
            agent_name="Ping Agent",
            protocols=["ping"],
        )
    )
    message_router.register_handler("ping-agent", handler)

    agent = BaseAgent(
        context=AgentContext(
            agent_id="requester",
            name="Requester",
            project_id="proj-1",
        )
    )

    response = await agent.request(
        target_agent="ping-agent",
        protocol="ping",
        payload={"msg": "hello"},
        timeout=5,
    )
    assert response["pong"] is True


def test_base_agent_register_in_protocol():
    from app.agents.base import AgentContext, BaseAgent

    agent = BaseAgent(
        context=AgentContext(
            agent_id="reg-test",
            name="Registration Test",
            project_id="proj-1",
        )
    )
    agent.register_in_protocol(
        protocols=["custom.protocol"],
        description="A custom test agent",
    )

    found = agent_registry.find_by_id("reg-test")
    assert found is not None
    assert "custom.protocol" in found.protocols

import pytest
import uuid

from app.core.agent_protocol import (
    AgentMessage,
    MessageRouter,
    SharedWorkspace,
    ConversationThread,
    message_router,
    shared_workspace,
)


class TestSharedWorkspace:
    def test_set_and_get(self):
        ws = SharedWorkspace()
        ws.set("key1", {"data": "value"}, created_by="agent-1")
        assert ws.get("key1") == {"data": "value"}

    def test_get_nonexistent(self):
        ws = SharedWorkspace()
        assert ws.get("nonexistent") is None

    def test_delete(self):
        ws = SharedWorkspace()
        ws.set("k", {"v": 1}, "a1")
        assert ws.delete("k") is True
        assert ws.get("k") is None

    def test_delete_nonexistent(self):
        ws = SharedWorkspace()
        assert ws.delete("nonexistent") is False

    def test_list_keys(self):
        ws = SharedWorkspace()
        ws.set("a", {}, "a1")
        ws.set("b", {}, "a2")
        keys = ws.list_keys()
        assert "a" in keys
        assert "b" in keys

    def test_ttl_expiry(self):
        ws = SharedWorkspace()
        ws.set("expires", {"v": 1}, "a1", ttl=0.001)
        import time
        time.sleep(0.01)
        assert ws.get("expires") is None

    def test_clear(self):
        ws = SharedWorkspace()
        ws.set("a", {}, "a1")
        ws.clear()
        assert ws.list_keys() == []

    def test_to_dict(self):
        ws = SharedWorkspace()
        ws.set("k", {"v": 1}, "a1")
        d = ws.to_dict()
        assert "k" in d
        assert d["k"]["value"] == {"v": 1}

    def test_global_workspace(self):
        assert isinstance(shared_workspace, SharedWorkspace)


class TestConversationThread:
    def test_create_thread(self):
        router = MessageRouter()
        thread = router.create_thread(
            protocol="test.protocol",
            participants=["agent-1", "agent-2"],
            context={"project": "test"},
        )
        assert thread.protocol == "test.protocol"
        assert thread.participants == ["agent-1", "agent-2"]
        assert thread.context == {"project": "test"}
        assert thread.status == "active"

    def test_get_thread(self):
        router = MessageRouter()
        created = router.create_thread("proto", ["a1"])
        found = router.get_thread(created.thread_id)
        assert found is not None
        assert found.thread_id == created.thread_id

    def test_get_thread_nonexistent(self):
        router = MessageRouter()
        assert router.get_thread("nonexistent") is None

    def test_list_threads(self):
        router = MessageRouter()
        router.create_thread("proto-1", ["a1"])
        router.create_thread("proto-2", ["a2"])
        router.create_thread("proto-1", ["a3"])
        assert len(router.list_threads()) == 3
        assert len(router.list_threads(protocol="proto-1")) == 2

    def test_close_thread(self):
        router = MessageRouter()
        created = router.create_thread("proto", ["a1"])
        assert router.close_thread(created.thread_id) is True
        thread = router.get_thread(created.thread_id)
        assert thread.status == "closed"

    def test_close_thread_nonexistent(self):
        router = MessageRouter()
        assert router.close_thread("nonexistent") is False

    def test_thread_message_tracking(self):
        router = MessageRouter()
        thread = router.create_thread("proto", ["a1", "a2"])
        msg = AgentMessage(
            message_id=str(uuid.uuid4()),
            protocol="proto",
            payload={},
            source_agent="a1",
            target_agent="a2",
        )
        # Simulate processing via event
        router._threads[thread.thread_id].messages.append(msg)
        assert len(thread.messages) == 1
        assert thread.messages[0].source_agent == "a1"

    def test_global_message_router(self):
        assert isinstance(message_router, MessageRouter)

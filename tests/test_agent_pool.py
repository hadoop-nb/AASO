import pytest

from app.core.agent_pool import AgentPool, AgentStatus, PooledAgent, agent_pool


@pytest.fixture
def pool():
    p = AgentPool()
    p.register("developer", "dev-001")
    p.register("qa", "qa-001")
    p.register("developer", "dev-002")
    return p


class TestAgentPool:
    def test_register(self):
        p = AgentPool()
        agent = p.register("developer", "my-dev")
        assert agent.agent_id == "my-dev"
        assert agent.agent_type == "developer"
        assert agent.status == AgentStatus.IDLE
        assert agent.is_available

    def test_register_generates_id(self):
        p = AgentPool()
        agent = p.register("developer")
        assert agent.agent_id.startswith("developer-")
        assert agent.agent_type == "developer"

    def test_register_duplicate_updates(self):
        p = AgentPool()
        p.register("developer", "dev-001")
        agent2 = p.register("qa", "dev-001", {"updated": True})
        assert agent2.agent_type == "qa"
        assert agent2.metadata == {"updated": True}

    def test_unregister(self, pool: AgentPool):
        assert pool.unregister("dev-001") is True
        assert pool.get_agent("dev-001") is None

    def test_unregister_nonexistent(self, pool: AgentPool):
        assert pool.unregister("nonexistent") is False

    def test_acquire_returns_idle_agent(self, pool: AgentPool):
        agent = pool.acquire("developer", task_id="task-1")
        assert agent is not None
        assert agent.status == AgentStatus.BUSY
        assert agent.current_task_id == "task-1"
        assert not agent.is_available

    def test_acquire_skips_busy_agents(self, pool: AgentPool):
        pool.acquire("developer", task_id="task-1")
        agent2 = pool.acquire("developer", task_id="task-2")
        assert agent2 is not None
        assert agent2.agent_id == "dev-002"

    def test_acquire_no_available(self, pool: AgentPool):
        pool.acquire("developer")
        pool.acquire("developer")
        agent = pool.acquire("developer")
        assert agent is None

    def test_acquire_no_agents_of_type(self, pool: AgentPool):
        agent = pool.acquire("nonexistent")
        assert agent is None

    def test_release(self, pool: AgentPool):
        pool.acquire("developer", task_id="task-1")
        assert pool.release("dev-001") is True
        agent = pool.get_agent("dev-001")
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task_id is None
        assert agent.completed_tasks == 1

    def test_release_with_error(self, pool: AgentPool):
        pool.acquire("developer")
        pool.release("dev-001", error=True)
        agent = pool.get_agent("dev-001")
        assert agent.error_count == 1

    def test_release_nonexistent(self, pool: AgentPool):
        assert pool.release("nonexistent") is False

    def test_mark_error(self, pool: AgentPool):
        assert pool.mark_error("dev-001") is True
        agent = pool.get_agent("dev-001")
        assert agent.status == AgentStatus.ERROR
        assert agent.error_count == 1

    def test_mark_error_nonexistent(self, pool: AgentPool):
        assert pool.mark_error("nonexistent") is False

    def test_get_agent(self, pool: AgentPool):
        agent = pool.get_agent("dev-001")
        assert agent is not None
        assert agent.agent_id == "dev-001"

    def test_get_agent_nonexistent(self, pool: AgentPool):
        assert pool.get_agent("nonexistent") is None

    def test_list_agents_all(self, pool: AgentPool):
        agents = pool.list_agents()
        assert len(agents) == 3

    def test_list_agents_by_type(self, pool: AgentPool):
        agents = pool.list_agents(agent_type="developer")
        assert len(agents) == 2
        assert all(a.agent_type == "developer" for a in agents)

    def test_list_agents_by_status(self, pool: AgentPool):
        pool.acquire("developer")
        idle = pool.list_agents(status=AgentStatus.IDLE)
        busy = pool.list_agents(status=AgentStatus.BUSY)
        assert len(idle) == 2
        assert len(busy) == 1

    def test_count_by_type(self, pool: AgentPool):
        counts = pool.count_by_type()
        assert counts == {"developer": 2, "qa": 1}

    def test_count_by_status(self, pool: AgentPool):
        pool.acquire("developer")
        statuses = pool.count_by_status()
        assert statuses.get("busy") == 1
        assert statuses.get("idle") == 2

    def test_pool_summary(self, pool: AgentPool):
        summary = pool.get_pool_summary()
        assert summary["total_agents"] == 3
        assert summary["available"] == 3
        assert summary["busy"] == 0

    def test_busy_duration(self, pool: AgentPool):
        pool.acquire("developer", task_id="t1")
        agent = pool.get_agent("dev-001")
        assert agent.busy_duration_seconds >= 0

    def test_global_pool(self):
        assert isinstance(agent_pool, AgentPool)

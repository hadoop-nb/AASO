import pytest

from app.services.analytics_service import AgentRunRecord, AnalyticsService


@pytest.fixture
def analytics():
    return AnalyticsService()


def test_record_run(analytics: AnalyticsService):
    record = AgentRunRecord(
        agent_type="developer",
        project_id="p1",
        task_id="t1",
        success=True,
        duration_ms=1500.0,
        files_generated=3,
    )
    analytics.record_run(record)
    assert len(analytics._runs) == 1


@pytest.mark.asyncio
async def test_get_agent_stats(analytics: AnalyticsService):
    analytics.record_run(AgentRunRecord("developer", "p1", "t1", True, 100.0, 2))
    analytics.record_run(AgentRunRecord("developer", "p1", "t2", True, 200.0, 1))
    analytics.record_run(AgentRunRecord("developer", "p1", "t3", False, 50.0, 0))
    analytics.record_run(AgentRunRecord("qa", "p1", "t4", True, 30.0, 0))

    dev_stats = await analytics.get_agent_stats("developer")
    assert dev_stats["total_runs"] == 3
    assert dev_stats["successes"] == 2
    assert dev_stats["failures"] == 1
    assert dev_stats["success_rate"] == 66.7
    assert dev_stats["total_files_generated"] == 3

    all_stats = await analytics.get_agent_stats()
    assert all_stats["total_runs"] == 4


@pytest.mark.asyncio
async def test_get_project_stats(analytics: AnalyticsService):
    analytics.record_run(AgentRunRecord("developer", "p1", "t1", True, 100.0, 2))
    analytics.record_run(AgentRunRecord("qa", "p1", "t2", True, 50.0, 0))
    analytics.record_run(AgentRunRecord("developer", "p2", "t3", True, 200.0, 1))

    stats = await analytics.get_project_stats("p1")
    assert stats["total_runs"] == 2
    assert stats["successes"] == 2
    assert "developer" in stats["per_agent"]
    assert "qa" in stats["per_agent"]

    empty = await analytics.get_project_stats("p3")
    assert empty["total_runs"] == 0


@pytest.mark.asyncio
async def test_get_recent_runs(analytics: AnalyticsService):
    for i in range(5):
        analytics.record_run(AgentRunRecord("developer", "p1", f"t{i}", True, float(i * 100), i))

    runs = await analytics.get_recent_runs(limit=3)
    assert len(runs) == 3

    dev_runs = await analytics.get_recent_runs(limit=10, agent_type="developer")
    assert len(dev_runs) == 5


@pytest.mark.asyncio
async def test_get_agent_stats_empty(analytics: AnalyticsService):
    stats = await analytics.get_agent_stats("nonexistent")
    assert stats["total_runs"] == 0

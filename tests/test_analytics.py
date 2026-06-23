import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun
from app.services.analytics_service import AnalyticsService


@pytest.fixture
def svc(session: AsyncSession):
    return AnalyticsService(session)


@pytest.mark.asyncio
async def test_record_and_get_run(svc: AnalyticsService, session: AsyncSession):
    run = await svc.record_run(
        agent_type="developer",
        agent_id="dev-001",
        project_id="p1",
        task_id="t1",
        success=True,
        duration_ms=1500.0,
        files_generated=3,
    )
    assert run is not None
    assert run.run_id is not None

    result = await svc.get_run(run.run_id)
    assert result is not None
    assert result["agent_type"] == "developer"
    assert result["success"] is True
    assert result["files_generated"] == 3


@pytest.mark.asyncio
async def test_get_agent_stats(svc: AnalyticsService, session: AsyncSession):
    await svc.record_run("developer", "dev-001", "p1", "t1", True, 100.0, 2)
    await svc.record_run("developer", "dev-001", "p1", "t2", True, 200.0, 1)
    await svc.record_run("developer", "dev-001", "p1", "t3", False, 50.0, 0)
    await svc.record_run("qa", "qa-001", "p1", "t4", True, 30.0, 0)

    dev_stats = await svc.get_agent_stats("developer")
    assert dev_stats["total_runs"] == 3
    assert dev_stats["successes"] == 2
    assert dev_stats["failures"] == 1
    assert dev_stats["total_files_generated"] == 3

    all_stats = await svc.get_agent_stats()
    assert all_stats["total_runs"] == 4


@pytest.mark.asyncio
async def test_get_project_stats(svc: AnalyticsService, session: AsyncSession):
    await svc.record_run("developer", "dev-001", "p1", "t1", True, 100.0, 2)
    await svc.record_run("qa", "qa-001", "p1", "t2", True, 50.0, 0)
    await svc.record_run("developer", "dev-002", "p2", "t3", True, 200.0, 1)

    stats = await svc.get_project_stats("p1")
    assert stats["total_runs"] == 2
    assert stats["successes"] == 2
    assert "developer" in stats["per_agent"]
    assert "qa" in stats["per_agent"]

    empty = await svc.get_project_stats("p3")
    assert empty["total_runs"] == 0


@pytest.mark.asyncio
async def test_get_recent_runs(svc: AnalyticsService, session: AsyncSession):
    for i in range(5):
        await svc.record_run("developer", "dev-001", "p1", f"t{i}", True, float(i * 100), i)

    runs = await svc.get_recent_runs(limit=3)
    assert len(runs) == 3

    dev_runs = await svc.get_recent_runs(limit=10, agent_type="developer")
    assert len(dev_runs) == 5


@pytest.mark.asyncio
async def test_get_agent_stats_empty(svc: AnalyticsService, session: AsyncSession):
    stats = await svc.get_agent_stats("nonexistent")
    assert stats["total_runs"] == 0

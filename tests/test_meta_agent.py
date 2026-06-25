from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.services.meta_agent_service import MetaAgentService


@pytest.mark.asyncio
async def test_generate_retrospective_empty(session: AsyncSession):
    svc = MetaAgentService(session)
    analysis = await svc.generate_retrospective("proj-empty", days=7)
    assert analysis.analysis_type == "retrospective"
    assert "0 runs" in analysis.summary or "0" in analysis.summary
    assert analysis.actionable is False


@pytest.mark.asyncio
async def test_generate_retrospective_with_runs(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-r", 5, True)
    _add_runs(session, "proj-r", 2, False)
    await session.flush()

    analysis = await svc.generate_retrospective("proj-r", days=30)
    details = __import__("json").loads(analysis.details_json)
    assert details["total_runs"] == 7
    assert details["successful"] == 5
    assert details["failed"] == 2
    assert analysis.actionable is True


@pytest.mark.asyncio
async def test_mine_failure_patterns(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-f", 10, True, agent_type="dev")
    _add_runs(session, "proj-f", 5, False, agent_type="qa")
    _add_runs(session, "proj-f", 1, False, agent_type="dev")
    await session.flush()

    analysis = await svc.mine_failure_patterns("proj-f")
    details = __import__("json").loads(analysis.details_json)
    patterns = {p["agent_type"]: p for p in details["patterns"]}
    assert "dev" in patterns
    assert "qa" in patterns
    assert patterns["qa"]["failure_rate_pct"] == 100.0
    assert analysis.actionable is True


@pytest.mark.asyncio
async def test_mine_failure_patterns_no_failures(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-ok", 5, True, agent_type="dev")
    await session.flush()

    analysis = await svc.mine_failure_patterns("proj-ok")
    details = __import__("json").loads(analysis.details_json)
    assert all(p["failure_rate_pct"] == 0 for p in details["patterns"])
    assert analysis.actionable is False


@pytest.mark.asyncio
async def test_mine_failure_patterns_no_runs(session: AsyncSession):
    svc = MetaAgentService(session)
    analysis = await svc.mine_failure_patterns("proj-none")
    details = __import__("json").loads(analysis.details_json)
    assert details["patterns"] == []


@pytest.mark.asyncio
async def test_performance_trends(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-t", 3, True, agent_type="dev")
    _add_runs(session, "proj-t", 2, False, agent_type="qa")
    await session.flush()

    analysis = await svc.get_performance_trends("proj-t", days=30)
    details = __import__("json").loads(analysis.details_json)
    assert details["days"] == 30
    assert len(details["trends"]) > 0


@pytest.mark.asyncio
async def test_generate_suggestions(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-s", 5, False, agent_type="dev")
    _add_runs(session, "proj-s", 5, True, agent_type="qa")
    await session.flush()

    analysis = await svc.generate_suggestions("proj-s")
    details = __import__("json").loads(analysis.details_json)
    suggestions = details["suggestions"]
    assert len(suggestions) > 0
    assert analysis.actionable is True


@pytest.mark.asyncio
async def test_generate_suggestions_no_issues(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-good", 5, True, agent_type="dev")
    await session.flush()

    analysis = await svc.generate_suggestions("proj-good")
    details = __import__("json").loads(analysis.details_json)
    assert len(details["suggestions"]) == 1
    assert details["suggestions"][0]["priority"] == "low"


@pytest.mark.asyncio
async def test_get_analyses(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-a", 3, False, agent_type="dev")
    await session.flush()

    a1 = await svc.generate_retrospective("proj-a", days=30)
    a2 = await svc.mine_failure_patterns("proj-a")

    all_a = await svc.get_analyses(project_id="proj-a")
    assert len(all_a) == 2

    filtered = await svc.get_analyses(project_id="proj-a", analysis_type="retrospective")
    assert len(filtered) == 1
    assert filtered[0]["analysis_id"] == a1.analysis_id


@pytest.mark.asyncio
async def test_get_analyses_global(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-g1", 3, True, agent_type="dev")
    _add_runs(session, "proj-g2", 3, False, agent_type="qa")
    await session.flush()

    await svc.generate_retrospective("proj-g1", days=7)
    await svc.mine_failure_patterns("proj-g2")

    all_a = await svc.get_analyses()
    assert len(all_a) == 2


@pytest.mark.asyncio
async def test_get_analysis_by_id(session: AsyncSession):
    svc = MetaAgentService(session)
    analysis = await svc.mine_failure_patterns("proj-get")
    fetched = await svc.get_analysis(analysis.analysis_id)
    assert fetched is not None
    assert fetched["analysis_id"] == analysis.analysis_id
    assert fetched["analysis_type"] == "failure_pattern"


@pytest.mark.asyncio
async def test_get_analysis_not_found(session: AsyncSession):
    svc = MetaAgentService(session)
    result = await svc.get_analysis("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_actionable(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-act", 2, False, agent_type="dev")
    await session.flush()

    await svc.mine_failure_patterns("proj-act")
    await svc.generate_retrospective("proj-act", days=7)

    actionable = await svc.get_actionable("proj-act")
    assert all(a["actionable"] for a in actionable)
    assert len(actionable) > 0


@pytest.mark.asyncio
async def test_no_actionable(session: AsyncSession):
    svc = MetaAgentService(session)
    _add_runs(session, "proj-clean", 5, True, agent_type="dev")
    await session.flush()

    await svc.get_performance_trends("proj-clean", days=30)
    actionable = await svc.get_actionable("proj-clean")
    assert len(actionable) == 0


def _add_runs(
    session: AsyncSession,
    project_id: str,
    count: int,
    success: bool,
    agent_type: str = "test",
):
    for i in range(count):
        session.add(
            AgentRun(
                project_id=project_id,
                agent_type=agent_type,
                agent_id=f"{agent_type}-{i}",
                success=success,
                duration_ms=100.0 + i * 10,
                error=None if success else f"Error {i}",
                executed_at=datetime.now(timezone.utc),
            )
        )

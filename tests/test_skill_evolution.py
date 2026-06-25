import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.skill_evolution_service import SkillEvolutionService


@pytest.mark.asyncio
async def test_record_assessment(session: AsyncSession):
    svc = SkillEvolutionService(session)
    a = await svc.record_assessment(
        agent_type="dev", agent_id="dev-001", score=7.5,
        confidence=0.8, task_id="task-1", project_id="proj-1",
        strengths="Good code", weaknesses="Missing tests",
    )
    assert a.assessment_id
    assert a.score == 7.5
    assert a.confidence == 0.8
    assert a.agent_type == "dev"
    assert a.strengths == "Good code"
    assert a.weaknesses == "Missing tests"


@pytest.mark.asyncio
async def test_record_assessment_invalid_score(session: AsyncSession):
    svc = SkillEvolutionService(session)
    with pytest.raises(ValueError, match="Score must be between 0 and 10"):
        await svc.record_assessment("dev", "dev-001", 11.0)
    with pytest.raises(ValueError, match="Score must be between 0 and 10"):
        await svc.record_assessment("dev", "dev-001", -1.0)


@pytest.mark.asyncio
async def test_record_assessment_invalid_confidence(session: AsyncSession):
    svc = SkillEvolutionService(session)
    with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
        await svc.record_assessment("dev", "dev-001", 5.0, confidence=1.5)


@pytest.mark.asyncio
async def test_get_agent_performance(session: AsyncSession):
    svc = SkillEvolutionService(session)
    await svc.record_assessment("dev", "dev-001", 8.0, 0.9)
    await svc.record_assessment("dev", "dev-001", 6.0, 0.7)
    await svc.record_assessment("qa", "qa-001", 9.0, 0.95)

    perfs = await svc.get_agent_performance()
    perf_map = {p["agent_type"]: p for p in perfs}

    assert perf_map["dev"]["assessments"] == 2
    assert perf_map["dev"]["avg_score"] == 7.0
    assert perf_map["qa"]["assessments"] == 1
    assert perf_map["qa"]["avg_score"] == 9.0


@pytest.mark.asyncio
async def test_get_agent_performance_filtered(session: AsyncSession):
    svc = SkillEvolutionService(session)
    await svc.record_assessment("dev", "dev-001", 8.0, 0.9)
    await svc.record_assessment("qa", "qa-001", 9.0, 0.95)

    perfs = await svc.get_agent_performance("dev")
    assert len(perfs) == 1
    assert perfs[0]["agent_type"] == "dev"


@pytest.mark.asyncio
async def test_get_assessment_history_by_agent(session: AsyncSession):
    svc = SkillEvolutionService(session)
    a1 = await svc.record_assessment("dev", "dev-001", 8.0)
    a2 = await svc.record_assessment("dev", "dev-001", 6.0)
    await svc.record_assessment("qa", "qa-001", 9.0)

    history = await svc.get_assessment_history(agent_type="dev")
    assert len(history) == 2
    ids = {h["assessment_id"] for h in history}
    assert a1.assessment_id in ids
    assert a2.assessment_id in ids


@pytest.mark.asyncio
async def test_get_assessment_history_by_project(session: AsyncSession):
    svc = SkillEvolutionService(session)
    a1 = await svc.record_assessment("dev", "dev-001", 8.0, project_id="proj-x")
    a2 = await svc.record_assessment("dev", "dev-002", 6.0, project_id="proj-x")
    await svc.record_assessment("dev", "dev-003", 9.0, project_id="proj-y")

    history = await svc.get_assessment_history(project_id="proj-x")
    assert len(history) == 2
    ids = {h["assessment_id"] for h in history}
    assert a1.assessment_id in ids
    assert a2.assessment_id in ids


@pytest.mark.asyncio
async def test_create_prompt_template(session: AsyncSession):
    svc = SkillEvolutionService(session)
    t = await svc.create_prompt_template(
        agent_type="dev",
        name="Developer v1",
        system_prompt="You are a developer",
        user_prompt_template="Write code for {task}",
        change_notes="Initial version",
    )
    assert t.template_id
    assert t.version == 1
    assert t.is_active is True


@pytest.mark.asyncio
async def test_create_prompt_template_auto_increments(session: AsyncSession):
    svc = SkillEvolutionService(session)
    t1 = await svc.create_prompt_template("dev", "v1", "prompt1")
    t2 = await svc.create_prompt_template("dev", "v2", "prompt2")
    assert t1.version == 1
    assert t2.version == 2
    assert t1.is_active is False  # deactivated
    assert t2.is_active is True


@pytest.mark.asyncio
async def test_get_active_prompt(session: AsyncSession):
    svc = SkillEvolutionService(session)
    result = await svc.get_active_prompt("dev")
    assert result is None

    await svc.create_prompt_template("dev", "v1", "prompt1")
    result = await svc.get_active_prompt("dev")
    assert result is not None
    assert result["version"] == 1
    assert result["name"] == "v1"


@pytest.mark.asyncio
async def test_list_prompt_templates(session: AsyncSession):
    svc = SkillEvolutionService(session)
    await svc.create_prompt_template("dev", "v1", "prompt1")
    await svc.create_prompt_template("dev", "v2", "prompt2")
    await svc.create_prompt_template("qa", "v1", "prompt_q")

    all_t = await svc.list_prompt_templates()
    assert len(all_t) == 3

    dev_t = await svc.list_prompt_templates(agent_type="dev")
    assert len(dev_t) == 2


@pytest.mark.asyncio
async def test_compare_ab_test(session: AsyncSession):
    svc = SkillEvolutionService(session)
    t1 = await svc.create_prompt_template("dev", "v1", "prompt A")
    t2 = await svc.create_prompt_template("dev", "v2", "prompt B")

    await svc.record_assessment("dev", "dev-001", 8.0)
    await svc.record_assessment("dev", "dev-001", 6.0)

    result = await svc.compare_ab_test("dev", 1, 2)
    assert result["version_a"]["version"] == 1
    assert result["version_b"]["version"] == 2
    assert result["comparison"]["version_a_assessments"] == 2
    assert result["comparison"]["version_a_avg_score"] == 7.0


@pytest.mark.asyncio
async def test_compare_ab_test_not_found(session: AsyncSession):
    svc = SkillEvolutionService(session)
    result = await svc.compare_ab_test("dev", 1, 99)
    assert "error" in result


@pytest.mark.asyncio
async def test_assessment_with_run_id(session: AsyncSession):
    svc = SkillEvolutionService(session)
    a = await svc.record_assessment(
        "dev", "dev-001", 8.0, run_id="run-abc",
        notes="Performed well",
    )
    assert a.run_id == "run-abc"
    assert a.notes == "Performed well"

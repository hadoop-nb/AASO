import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.planning_service import PlanningService


@pytest.mark.asyncio
async def test_create_plan(session: AsyncSession):
    svc = PlanningService(session)
    plan = await svc.create_plan(
        project_id="proj-1", goal="Build a user authentication system",
        priority="high", notes="Critical path item",
    )
    assert plan.plan_id
    assert plan.project_id == "proj-1"
    assert plan.goal == "Build a user authentication system"
    assert plan.priority == "high"
    assert plan.status == "draft"
    assert plan.notes == "Critical path item"


@pytest.mark.asyncio
async def test_create_plan_invalid_priority(session: AsyncSession):
    svc = PlanningService(session)
    with pytest.raises(ValueError, match="Priority must be"):
        await svc.create_plan("proj-1", "goal", priority="urgent")


@pytest.mark.asyncio
async def test_get_plan(session: AsyncSession):
    svc = PlanningService(session)
    created = await svc.create_plan("proj-1", "Build feature X")
    result = await svc.get_plan(created.plan_id)
    assert result is not None
    assert result["goal"] == "Build feature X"
    assert result["plan_id"] == created.plan_id


@pytest.mark.asyncio
async def test_get_plan_not_found(session: AsyncSession):
    svc = PlanningService(session)
    result = await svc.get_plan("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_plans(session: AsyncSession):
    svc = PlanningService(session)
    await svc.create_plan("proj-1", "Goal A")
    await svc.create_plan("proj-1", "Goal B")
    await svc.create_plan("proj-2", "Goal C")

    plans = await svc.list_plans("proj-1")
    assert len(plans) == 2
    goals = {p["goal"] for p in plans}
    assert goals == {"Goal A", "Goal B"}


@pytest.mark.asyncio
async def test_update_plan_status(session: AsyncSession):
    svc = PlanningService(session)
    created = await svc.create_plan("proj-1", "Goal")
    result = await svc.update_plan_status(created.plan_id, "active")
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_update_plan_status_invalid(session: AsyncSession):
    svc = PlanningService(session)
    created = await svc.create_plan("proj-1", "Goal")
    with pytest.raises(ValueError, match="Status must be"):
        await svc.update_plan_status(created.plan_id, "invalid_status")


@pytest.mark.asyncio
async def test_update_plan_status_not_found(session: AsyncSession):
    svc = PlanningService(session)
    result = await svc.update_plan_status("nonexistent", "active")
    assert result is None


@pytest.mark.asyncio
async def test_add_plan_task(session: AsyncSession):
    svc = PlanningService(session)
    plan = await svc.create_plan("proj-1", "Goal")
    task = await svc.add_plan_task(
        plan_id=plan.plan_id,
        title="Write tests",
        description="Write unit tests for the module",
        priority="high",
        estimated_hours=4.0,
        dependencies=["task-1"],
        assigned_agent_type="qa",
        sort_order=1,
    )
    assert task.task_id
    assert task.title == "Write tests"
    assert task.description == "Write unit tests for the module"
    assert task.priority == "high"
    assert task.estimated_hours == 4.0
    assert task.assigned_agent_type == "qa"
    assert task.sort_order == 1
    assert task.status == "pending"


@pytest.mark.asyncio
async def test_add_plan_task_invalid_priority(session: AsyncSession):
    svc = PlanningService(session)
    plan = await svc.create_plan("proj-1", "Goal")
    with pytest.raises(ValueError, match="Priority must be"):
        await svc.add_plan_task(plan.plan_id, "Task", priority="invalid")


@pytest.mark.asyncio
async def test_add_plan_task_plan_not_found(session: AsyncSession):
    svc = PlanningService(session)
    with pytest.raises(ValueError, match="Plan .* not found"):
        await svc.add_plan_task("nonexistent", "Task")


@pytest.mark.asyncio
async def test_update_plan_task(session: AsyncSession):
    svc = PlanningService(session)
    plan = await svc.create_plan("proj-1", "Goal")
    task = await svc.add_plan_task(plan.plan_id, "Initial title")
    result = await svc.update_plan_task(
        task.task_id,
        title="Updated title",
        status="in_progress",
        priority="high",
        risk_score=0.3,
        risk_factors=["tight deadline", "complex logic"],
    )
    assert result["title"] == "Updated title"
    assert result["status"] == "in_progress"
    assert result["priority"] == "high"
    assert result["risk_score"] == 0.3
    assert "tight deadline" in result["risk_factors"]


@pytest.mark.asyncio
async def test_update_plan_task_not_found(session: AsyncSession):
    svc = PlanningService(session)
    result = await svc.update_plan_task("nonexistent", title="New title")
    assert result is None


@pytest.mark.asyncio
async def test_delete_plan_task(session: AsyncSession):
    svc = PlanningService(session)
    plan = await svc.create_plan("proj-1", "Goal")
    task = await svc.add_plan_task(plan.plan_id, "To delete")
    deleted = await svc.delete_plan_task(task.task_id)
    assert deleted is True
    deleted2 = await svc.delete_plan_task(task.task_id)
    assert deleted2 is False


@pytest.mark.asyncio
async def test_get_plan_tasks(session: AsyncSession):
    svc = PlanningService(session)
    plan = await svc.create_plan("proj-1", "Goal")
    t1 = await svc.add_plan_task(plan.plan_id, "Task A", sort_order=2)
    t2 = await svc.add_plan_task(plan.plan_id, "Task B", sort_order=1)

    tasks = await svc.get_plan_tasks(plan.plan_id)
    assert len(tasks) == 2
    assert tasks[0]["task_id"] == t2.task_id  # lower sort_order first
    assert tasks[1]["task_id"] == t1.task_id


@pytest.mark.asyncio
async def test_analyze_risks_empty(session: AsyncSession):
    svc = PlanningService(session)
    plan = await svc.create_plan("proj-1", "Goal")
    result = await svc.analyze_risks(plan.plan_id)
    assert result["overall_risk"] is None
    assert result["high_risk_tasks"] == []


@pytest.mark.asyncio
async def test_analyze_risks(session: AsyncSession):
    svc = PlanningService(session)
    plan = await svc.create_plan("proj-1", "Goal")
    t1 = await svc.add_plan_task(plan.plan_id, "Safe task")
    t2 = await svc.add_plan_task(plan.plan_id, "Risky task")
    await svc.update_plan_task(t1.task_id, risk_score=0.2)
    await svc.update_plan_task(t2.task_id, risk_score=0.85)

    result = await svc.analyze_risks(plan.plan_id)
    assert result["overall_risk"] == 0.53  # (0.85 + 0.2) / 2 = 0.525 -> 0.53
    assert result["high_risk_count"] == 1
    assert result["medium_risk_count"] == 0
    assert result["high_risk_tasks"][0]["task_id"] == t2.task_id


@pytest.mark.asyncio
async def test_prioritize_tasks(session: AsyncSession):
    svc = PlanningService(session)
    plan = await svc.create_plan("proj-1", "Goal")
    t_low = await svc.add_plan_task(plan.plan_id, "Low priority", priority="low")
    t_high = await svc.add_plan_task(plan.plan_id, "High priority", priority="high")
    t_crit = await svc.add_plan_task(plan.plan_id, "Critical priority", priority="critical")

    sorted_tasks = await svc.prioritize_tasks(plan.plan_id)
    assert sorted_tasks[0]["task_id"] == t_crit.task_id
    assert sorted_tasks[1]["task_id"] == t_high.task_id
    assert sorted_tasks[2]["task_id"] == t_low.task_id


@pytest.mark.asyncio
async def test_work_breakdown(session: AsyncSession):
    svc = PlanningService(session)
    result = await svc.work_breakdown(
        goal="Build a REST API",
        project_id="proj-1",
        priority="high",
    )
    assert "plan_id" in result
    assert result["goal"] == "Build a REST API"
    assert len(result["phases"]) == 5

    tasks = await svc.get_plan_tasks(result["plan_id"])
    assert len(tasks) >= 5  # at least 5 phase-level tasks

    plan = await svc.get_plan(result["plan_id"])
    assert plan["priority"] == "high"

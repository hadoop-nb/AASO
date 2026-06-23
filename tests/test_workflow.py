import pytest

from app.core.workflow import Workflow, WorkflowEngine, WorkflowStep, WorkflowStatus


@pytest.fixture
def engine():
    return WorkflowEngine()


@pytest.mark.asyncio
async def test_simple_workflow_succeeds(engine: WorkflowEngine):
    async def step_a(**kwargs) -> dict:
        return {"result": "A done"}

    async def step_b(**kwargs) -> dict:
        prev = kwargs.get("step_a", {})
        return {"result": f"B done after {prev.get('result')}"}

    workflow = Workflow(
        workflow_id="w1",
        name="Simple",
        project_id="p1",
        steps=[
            WorkflowStep(name="step_a", handler=step_a, agent_type="test"),
            WorkflowStep(name="step_b", handler=step_b, agent_type="test", depends_on=["step_a"]),
        ],
    )
    engine.register(workflow)
    result = await engine.execute("w1")
    assert result["success"] is True
    assert result["step_results"]["step_a"]["result"] == "A done"
    assert "B done" in result["step_results"]["step_b"]["result"]


@pytest.mark.asyncio
async def test_workflow_step_failure(engine: WorkflowEngine):
    async def good_step(**kwargs) -> dict:
        return {"ok": True}

    async def bad_step(**kwargs) -> dict:
        raise ValueError("step failed")

    workflow = Workflow(
        workflow_id="w2",
        name="Failing",
        project_id="p1",
        steps=[
            WorkflowStep(name="good", handler=good_step, agent_type="test"),
            WorkflowStep(name="bad", handler=bad_step, agent_type="test", max_retries=1),
        ],
    )
    engine.register(workflow)
    result = await engine.execute("w2")
    assert result["success"] is False
    assert "step failed" in result["error"]


@pytest.mark.asyncio
async def test_workflow_not_found(engine: WorkflowEngine):
    result = await engine.execute("nonexistent")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_workflow_cancel(engine: WorkflowEngine):
    async def slow_step(**kwargs) -> dict:
        return {"done": True}

    workflow = Workflow(
        workflow_id="w3",
        name="Cancel",
        project_id="p1",
        steps=[WorkflowStep(name="s1", handler=slow_step, agent_type="test")],
    )
    engine.register(workflow)
    engine._workflows["w3"].status = WorkflowStatus.RUNNING
    result = engine.cancel("w3")
    assert result is True
    assert engine.get("w3").status == WorkflowStatus.CANCELLED


@pytest.mark.asyncio
async def test_workflow_list_by_project(engine: WorkflowEngine):
    w1 = Workflow("w-p1a", "p1a", "p1", [])
    w2 = Workflow("w-p1b", "p1b", "p1", [])
    w3 = Workflow("w-p2", "p2", "p2", [])
    engine.register(w1)
    engine.register(w2)
    engine.register(w3)

    p1_workflows = engine.list_by_project("p1")
    assert len(p1_workflows) == 2

    p2_workflows = engine.list_by_project("p2")
    assert len(p2_workflows) == 1

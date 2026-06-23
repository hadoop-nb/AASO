import pytest

from app.core.event_bus import Event, event_bus
from app.core.pipeline import PipelineRunner, PipelineStatus


@pytest.fixture
def runner():
    r = PipelineRunner()
    r._ensure_subscribed()
    return r


@pytest.mark.asyncio
async def test_create_pipeline(runner: PipelineRunner):
    pipeline = runner.create_pipeline(
        pipeline_id="pipe-1",
        project_id="p1",
        goal="Build feature",
        steps=[
            {"agent_type": "developer", "config": {}},
            {"agent_type": "qa", "config": {}},
        ],
    )
    assert pipeline.pipeline_id == "pipe-1"
    assert pipeline.project_id == "p1"
    assert len(pipeline.steps) == 2
    assert pipeline.status == PipelineStatus.PENDING


@pytest.mark.asyncio
async def test_get_pipeline(runner: PipelineRunner):
    runner.create_pipeline("pipe-1", "p1", "goal", [{"agent_type": "developer", "config": {}}])
    pipeline = runner.get_pipeline("pipe-1")
    assert pipeline is not None
    assert pipeline.pipeline_id == "pipe-1"

    missing = runner.get_pipeline("nonexistent")
    assert missing is None


@pytest.mark.asyncio
async def test_list_pipelines(runner: PipelineRunner):
    runner.create_pipeline("p1", "proj1", "g1", [{"agent_type": "developer", "config": {}}])
    runner.create_pipeline("p2", "proj1", "g2", [{"agent_type": "developer", "config": {}}])
    runner.create_pipeline("p3", "proj2", "g3", [{"agent_type": "developer", "config": {}}])

    proj1 = runner.list_pipelines("proj1")
    assert len(proj1) == 2

    proj2 = runner.list_pipelines("proj2")
    assert len(proj2) == 1


@pytest.mark.asyncio
async def test_start_pipeline_no_handler(runner: PipelineRunner):
    runner.create_pipeline("pipe-1", "p1", "goal", [{"agent_type": "unknown", "config": {}}])
    result = await runner.start_pipeline("pipe-1")
    assert result["success"] is False
    assert "No handler for unknown" in result["error"]


@pytest.mark.asyncio
async def test_start_nonexistent_pipeline(runner: PipelineRunner):
    result = await runner.start_pipeline("nonexistent")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_pipeline_completed_event(runner: PipelineRunner):
    received = []

    async def on_completed(event: Event):
        received.append(event)

    event_bus.subscribe("pipeline:completed", on_completed)

    async def stub_handler(**kwargs) -> dict:
        return {"success": True, "files": ["f1"]}

    runner.register_handler("developer", stub_handler)
    runner.create_pipeline("pipe-evt", "p1", "goal", [{"agent_type": "developer", "config": {}}])
    await runner.start_pipeline("pipe-evt")

    assert len(received) == 1
    assert received[0].data["pipeline_id"] == "pipe-evt"

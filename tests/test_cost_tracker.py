import pytest
from unittest.mock import AsyncMock

from app.models.llm_cost import LLMCost
from app.services.cost_tracker import CostTracker, cost_tracker


@pytest.mark.asyncio
async def test_record_call_in_memory():
    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock()

    tracker = CostTracker()
    record = await tracker.record_call(
        model="test-model",
        provider="test",
        prompt_tokens=100,
        completion_tokens=50,
        project_id="proj-1",
        agent_type="developer",
    )
    assert record.model == "test-model"
    assert record.provider == "test"
    assert record.prompt_tokens == 100
    assert record.completion_tokens == 50
    assert record.total_tokens == 150
    assert record.project_id == "proj-1"
    assert record.agent_type == "developer"

    cached = tracker.get_cached_costs()
    assert len(cached) == 1
    assert cached[0].model == "test-model"


@pytest.mark.asyncio
async def test_record_call_with_session():
    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock(return_value=LLMCost(
        cost_id="test-id", model="m", provider="p",
        prompt_tokens=10, completion_tokens=5,
    ))

    tracker = CostTracker()
    tracker._repo = mock_repo

    record = await tracker.record_call(
        model="m", provider="p", prompt_tokens=10, completion_tokens=5,
    )
    assert record.model == "m"
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_estimate_tokens():
    tracker = CostTracker()
    text = "Hello world, this is a test!"
    estimated = tracker.estimate_tokens(text)
    assert estimated == len(text) // 4
    assert estimated == 7


@pytest.mark.asyncio
async def test_get_project_summary_no_session():
    tracker = CostTracker()
    summary = await tracker.get_project_summary("proj-1")
    assert summary["project_id"] == "proj-1"
    assert summary["total_calls"] == 0
    assert summary["total_tokens"] == 0
    assert summary["total_cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_get_overall_stats_no_session():
    tracker = CostTracker()
    stats = await tracker.get_overall_stats()
    assert stats["total_calls"] == 0


@pytest.mark.asyncio
async def test_get_cost_by_model_no_session():
    tracker = CostTracker()
    result = await tracker.get_cost_by_model()
    assert result == []


@pytest.mark.asyncio
async def test_global_cost_tracker_is_singleton():
    assert cost_tracker is not None
    assert isinstance(cost_tracker, CostTracker)

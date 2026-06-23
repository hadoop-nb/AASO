import pytest

from app.services.experience_service import ExperienceService


@pytest.mark.asyncio
async def test_record_feedback(session):
    exp = ExperienceService(session)
    await exp.record_feedback("lesson", "l1", 4.5, "Very helpful")
    key = "lesson_l1"
    assert key in exp._feedback_scores
    assert exp._feedback_scores[key] == 4.5


@pytest.mark.asyncio
async def test_get_weighted_experiences_no_memory(session):
    exp = ExperienceService(session)
    results = await exp.get_weighted_experiences("p1", "test query")
    assert results == []


@pytest.mark.asyncio
async def test_get_top_lessons_no_memory(session):
    exp = ExperienceService(session)
    results = await exp.get_top_lessons("p1", "test query")
    assert results == []


@pytest.mark.asyncio
async def test_get_top_decisions_no_memory(session):
    exp = ExperienceService(session)
    results = await exp.get_top_decisions("p1", "test query")
    assert results == []


@pytest.mark.asyncio
async def test_get_project_stats(session):
    exp = ExperienceService(session)
    stats = await exp.get_project_stats("p1")
    assert stats["project_id"] == "p1"
    assert stats["total_decisions"] == 0
    assert stats["total_lessons"] == 0
    assert stats["average_feedback_score"] == 0.0


@pytest.mark.asyncio
async def test_get_project_stats_with_feedbacks(session):
    exp = ExperienceService(session)
    await exp.record_feedback("lesson", "l1", 4.0, "good")
    await exp.record_feedback("lesson", "l2", 3.0, "ok")
    stats = await exp.get_project_stats("p1")
    assert stats["total_feedbacks"] == 2
    assert stats["average_feedback_score"] == 3.5

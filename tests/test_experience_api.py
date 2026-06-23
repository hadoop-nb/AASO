import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_record_feedback(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Exp Test"})
    pid = proj.json()["project_id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/experience/feedback",
        json={"entity_type": "lesson", "entity_id": "l1", "score": 4.5, "comment": "Great lesson"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_top_lessons(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Top Lessons"})
    pid = proj.json()["project_id"]

    resp = await client.get(
        f"/api/v1/projects/{pid}/experience/top-lessons",
        params={"query": "architecture decision"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_top_decisions(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Top Decisions"})
    pid = proj.json()["project_id"]

    resp = await client.get(
        f"/api/v1/projects/{pid}/experience/top-decisions",
        params={"query": "framework choice"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_experience_stats(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Exp Stats"})
    pid = proj.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{pid}/experience/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == pid

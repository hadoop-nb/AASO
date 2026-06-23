import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_agent_stats(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/agents/stats")
    assert resp.status_code == 200
    assert "total_runs" in resp.json()


@pytest.mark.asyncio
async def test_analytics_agent_stats_filtered(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/agents/stats?agent_type=developer")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_project_stats(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Analytics Project"})
    pid = proj.json()["project_id"]
    resp = await client.get(f"/api/v1/analytics/projects/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == pid


@pytest.mark.asyncio
async def test_analytics_recent_runs(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/runs")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_recent_runs_filtered(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/runs?agent_type=developer&limit=5")
    assert resp.status_code == 200

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import get_db
from app.models.llm_cost import LLMCost


@pytest.mark.asyncio
async def test_get_project_costs_empty(client: AsyncClient, session: AsyncSession):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Cost Test", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{pid}/costs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == pid
    assert data["total_calls"] == 0
    assert data["total_cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_get_project_cost_details_empty(client: AsyncClient, session: AsyncSession):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Cost Detail", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{pid}/costs/details")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_overall_costs_empty(client: AsyncClient):
    resp = await client.get("/api/v1/costs/overall")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_calls" in data


@pytest.mark.asyncio
async def test_costs_by_model_empty(client: AsyncClient):
    resp = await client.get("/api/v1/costs/by-model")
    assert resp.status_code == 200
    assert resp.json() == []

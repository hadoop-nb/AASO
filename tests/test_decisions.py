import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_decision(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "Decision Project"}
    )
    pid = proj_resp.json()["project_id"]
    payload = {
        "question": "FastAPI vs Flask?",
        "alternatives": ["FastAPI", "Flask", "Django"],
        "selected": "FastAPI",
        "reason": "Async support, auto-docs, Pydantic integration",
    }
    response = await client.post(
        f"/api/v1/projects/{pid}/decisions", json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["question"] == "FastAPI vs Flask?"
    assert data["selected"] == "FastAPI"


@pytest.mark.asyncio
async def test_list_decisions(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "List Decisions"}
    )
    pid = proj_resp.json()["project_id"]
    await client.post(
        f"/api/v1/projects/{pid}/decisions",
        json={
            "question": "DB?",
            "alternatives": ["PG", "MySQL"],
            "selected": "PG",
            "reason": "JSONB support",
        },
    )
    response = await client.get(
        f"/api/v1/projects/{pid}/decisions"
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1

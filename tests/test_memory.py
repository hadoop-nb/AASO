import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_query_memory(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "Memory Test"}
    )
    pid = proj_resp.json()["project_id"]

    await client.post(
        f"/api/v1/projects/{pid}/decisions",
        json={
            "question": "Which framework?",
            "alternatives": ["FastAPI", "Flask"],
            "selected": "FastAPI",
            "reason": "Async performance",
        },
    )

    response = await client.post(
        f"/api/v1/projects/{pid}/query",
        json={"query": "framework decision", "limit": 5},
    )
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)

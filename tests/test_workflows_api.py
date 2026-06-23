import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_workflow(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "WF Project"})
    pid = proj.json()["project_id"]

    create_resp = await client.post(
        f"/api/v1/projects/{pid}/workflows",
        json={
            "name": "Test Workflow",
            "steps": [
                {"name": "develop", "agent_type": "developer", "depends_on": []},
            ],
        },
    )
    assert create_resp.status_code == 201
    wid = create_resp.json()["workflow_id"]

    get_resp = await client.get(f"/api/v1/projects/{pid}/workflows/{wid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Test Workflow"


@pytest.mark.asyncio
async def test_list_workflows(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "List WF"})
    pid = proj.json()["project_id"]

    await client.post(
        f"/api/v1/projects/{pid}/workflows",
        json={"name": "WF1", "steps": [{"name": "s1", "agent_type": "developer", "depends_on": []}]},
    )
    await client.post(
        f"/api/v1/projects/{pid}/workflows",
        json={"name": "WF2", "steps": [{"name": "s1", "agent_type": "developer", "depends_on": []}]},
    )

    resp = await client.get(f"/api/v1/projects/{pid}/workflows")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_cancel_nonexistent_workflow(client: AsyncClient):
    resp = await client.post("/api/v1/projects/p1/workflows/bad-id/cancel")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_workflow(client: AsyncClient):
    resp = await client.get("/api/v1/projects/p1/workflows/nonexistent")
    assert resp.status_code == 404

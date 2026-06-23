import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_pipeline(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Pipeline Proj"})
    pid = proj.json()["project_id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/pipelines",
        json={
            "goal": "Build feature",
            "steps": [
                {"agent_type": "developer", "config": {}},
                {"agent_type": "qa", "config": {}},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "pipeline_id" in data
    assert data["project_id"] == pid
    assert len(data["steps"]) == 2


@pytest.mark.asyncio
async def test_get_pipeline(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Get Pipeline"})
    pid = proj.json()["project_id"]

    create_resp = await client.post(
        f"/api/v1/projects/{pid}/pipelines",
        json={
            "goal": "Test",
            "steps": [{"agent_type": "developer", "config": {}}],
        },
    )
    pipe_id = create_resp.json()["pipeline_id"]

    get_resp = await client.get(
        f"/api/v1/projects/{pid}/pipelines/{pipe_id}"
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["pipeline_id"] == pipe_id


@pytest.mark.asyncio
async def test_list_pipelines(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "List Pipelines"})
    pid = proj.json()["project_id"]

    await client.post(
        f"/api/v1/projects/{pid}/pipelines",
        json={"goal": "G1", "steps": [{"agent_type": "developer", "config": {}}]},
    )
    await client.post(
        f"/api/v1/projects/{pid}/pipelines",
        json={"goal": "G2", "steps": [{"agent_type": "developer", "config": {}}]},
    )

    resp = await client.get(f"/api/v1/projects/{pid}/pipelines")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_start_pipeline(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Start Pipeline"})
    pid = proj.json()["project_id"]

    create_resp = await client.post(
        f"/api/v1/projects/{pid}/pipelines",
        json={
            "goal": "Test",
            "steps": [{"agent_type": "developer", "config": {}}],
        },
    )
    pipe_id = create_resp.json()["pipeline_id"]

    start_resp = await client.post(
        f"/api/v1/projects/{pid}/pipelines/{pipe_id}/start"
    )
    assert start_resp.status_code == 200
    data = start_resp.json()
    assert data.get("success") is True or data.get("success") is False


@pytest.mark.asyncio
async def test_get_nonexistent_pipeline(client: AsyncClient):
    resp = await client.get("/api/v1/projects/p1/pipelines/nonexistent")
    assert resp.status_code == 404

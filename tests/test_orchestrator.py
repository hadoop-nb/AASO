import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_orchestrate_goal(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Orchestrate Project",
            "description": "Test orchestration",
        },
    )
    pid = proj_resp.json()["project_id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/orchestrate",
        json={"goal": "Build a simple calculator API"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    assert data["project_id"] == pid
    assert "run_id" in data
    assert len(data.get("sub_tasks", [])) >= 1
    assert len(data.get("all_file_ids", [])) >= 0


@pytest.mark.asyncio
async def test_orchestrate_get_run(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Get Run Test"},
    )
    pid = proj_resp.json()["project_id"]

    create_resp = await client.post(
        f"/api/v1/projects/{pid}/orchestrate",
        json={"goal": "Build a simple to-do list API"},
    )
    run_id = create_resp.json()["run_id"]

    get_resp = await client.get(
        f"/api/v1/projects/{pid}/orchestrate/{run_id}"
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["run_id"] == run_id
    assert get_resp.json()["project_id"] == pid


@pytest.mark.asyncio
async def test_orchestrate_list_runs(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "List Runs Test"},
    )
    pid = proj_resp.json()["project_id"]

    await client.post(
        f"/api/v1/projects/{pid}/orchestrate",
        json={"goal": "Goal 1"},
    )
    await client.post(
        f"/api/v1/projects/{pid}/orchestrate",
        json={"goal": "Goal 2"},
    )

    resp = await client.get(f"/api/v1/projects/{pid}/orchestrate")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_orchestrate_nonexistent_run(client: AsyncClient):
    resp = await client.get(
        "/api/v1/projects/p999/orchestrate/nonexistent"
    )
    assert resp.status_code == 404

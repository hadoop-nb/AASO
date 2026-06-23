import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "Task Project"}
    )
    pid = proj_resp.json()["project_id"]
    payload = {"title": "Test Task", "priority": "high"}
    response = await client.post(
        f"/api/v1/projects/{pid}/tasks", json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "List Tasks"}
    )
    pid = proj_resp.json()["project_id"]
    await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={"title": "Task 1"},
    )
    await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={"title": "Task 2"},
    )
    response = await client.get(f"/api/v1/projects/{pid}/tasks")
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_update_task(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "Update Task"}
    )
    pid = proj_resp.json()["project_id"]
    task_resp = await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={"title": "Update Me"},
    )
    tid = task_resp.json()["task_id"]
    response = await client.put(
        f"/api/v1/projects/{pid}/tasks/{tid}",
        json={"status": "in_progress", "completion_percentage": 50},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_complete_task_sets_100(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "Complete Task"}
    )
    pid = proj_resp.json()["project_id"]
    task_resp = await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={"title": "Complete Me"},
    )
    tid = task_resp.json()["task_id"]
    await client.put(
        f"/api/v1/projects/{pid}/tasks/{tid}",
        json={"status": "in_progress"},
    )
    response = await client.put(
        f"/api/v1/projects/{pid}/tasks/{tid}",
        json={"status": "completed"},
    )
    assert response.status_code == 200
    assert response.json()["completion_percentage"] == 100

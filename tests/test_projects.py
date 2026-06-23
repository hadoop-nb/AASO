import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    payload = {"name": "Test Project", "description": "A test project"}
    response = await client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["status"] == "created"
    assert "project_id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient):
    await client.post("/api/v1/projects", json={"name": "P1"})
    await client.post("/api/v1/projects", json={"name": "P2"})
    response = await client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/projects", json={"name": "Get Me"}
    )
    pid = create_resp.json()["project_id"]
    response = await client.get(f"/api/v1/projects/{pid}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Me"


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/projects", json={"name": "Old Name"}
    )
    pid = create_resp.json()["project_id"]
    response = await client.put(
        f"/api/v1/projects/{pid}",
        json={"name": "New Name", "status": "in_progress"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/projects", json={"name": "Delete Me"}
    )
    pid = create_resp.json()["project_id"]
    response = await client.delete(f"/api/v1/projects/{pid}")
    assert response.status_code == 204
    get_resp = await client.get(f"/api/v1/projects/{pid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_project_summary(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/projects", json={"name": "Summary Test"}
    )
    pid = create_resp.json()["project_id"]
    response = await client.get(f"/api/v1/projects/{pid}/summary")
    assert response.status_code == 200
    assert response.json()["total_tasks"] == 0


@pytest.mark.asyncio
async def test_project_report(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/projects", json={"name": "Report Test"}
    )
    pid = create_resp.json()["project_id"]
    response = await client.get(f"/api/v1/projects/{pid}/report")
    assert response.status_code == 200
    assert "task_breakdown" in response.json()

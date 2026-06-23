import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_code_file_directly(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "Code Project"}
    )
    pid = proj_resp.json()["project_id"]

    task_resp = await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={"title": "Code Task"},
    )
    tid = task_resp.json()["task_id"]

    payload = {
        "path": "src/main.py",
        "summary": "Main entry point",
        "content": 'print("hello")',
        "language": "python",
    }
    response = await client.post(
        f"/api/v1/projects/{pid}/code", json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["path"] == "src/main.py"
    assert "file_id" in data


@pytest.mark.asyncio
async def test_list_code_files(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "List Code"}
    )
    pid = proj_resp.json()["project_id"]

    await client.post(
        f"/api/v1/projects/{pid}/code",
        json={
            "path": "a.py",
            "summary": "File A",
            "content": "a",
            "language": "python",
        },
    )
    await client.post(
        f"/api/v1/projects/{pid}/code",
        json={
            "path": "b.py",
            "summary": "File B",
            "content": "b",
            "language": "python",
        },
    )

    response = await client.get(
        f"/api/v1/projects/{pid}/code"
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_get_code_file(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "Get Code"}
    )
    pid = proj_resp.json()["project_id"]

    create_resp = await client.post(
        f"/api/v1/projects/{pid}/code",
        json={
            "path": "app.py",
            "summary": "App file",
            "content": "app code",
            "language": "python",
        },
    )
    fid = create_resp.json()["file_id"]

    response = await client.get(
        f"/api/v1/projects/{pid}/code/{fid}"
    )
    assert response.status_code == 200
    assert response.json()["path"] == "app.py"

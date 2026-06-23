import pytest


@pytest.mark.asyncio
async def test_list_threads_empty(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Collab Test", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{pid}/collaboration/threads")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_thread_nonexistent(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Collab Test 2", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{pid}/collaboration/threads/nonexistent")
    assert resp.status_code == 200
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_close_thread_nonexistent(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Collab Test 3", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.post(f"/api/v1/projects/{pid}/collaboration/threads/nonexistent/close")
    assert resp.status_code == 200
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_workspace_empty(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Workspace Test", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{pid}/collaboration/workspace")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


@pytest.mark.asyncio
async def test_workspace_set_and_get(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Workspace Test 2", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    put_resp = await client.put(
        f"/api/v1/projects/{pid}/collaboration/workspace/test-key",
        json={"value": {"msg": "hello"}, "created_by": "tester"},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["success"] is True

    get_resp = await client.get(
        f"/api/v1/projects/{pid}/collaboration/workspace/test-key"
    )
    assert get_resp.status_code == 200
    assert get_resp.json() == {"msg": "hello"}


@pytest.mark.asyncio
async def test_workspace_get_nonexistent(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Workspace Test 3", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.get(
        f"/api/v1/projects/{pid}/collaboration/workspace/nonexistent"
    )
    assert resp.status_code == 200
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_workspace_delete(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Workspace Test 4", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    await client.put(
        f"/api/v1/projects/{pid}/collaboration/workspace/to-delete",
        json={"value": {"x": 1}, "created_by": "tester"},
    )

    del_resp = await client.delete(
        f"/api/v1/projects/{pid}/collaboration/workspace/to-delete"
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

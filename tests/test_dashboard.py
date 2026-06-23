import pytest


@pytest.mark.asyncio
async def test_overview_page(client):
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_project_list_page(client):
    resp = await client.get("/dashboard/projects")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_project_detail_page(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Dashboard Test", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.get(f"/dashboard/projects/{pid}")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_project_detail_not_found(client):
    resp = await client.get("/dashboard/projects/nonexistent")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_workforce_page(client):
    resp = await client.get("/dashboard/workforce")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_costs_page(client):
    resp = await client.get("/dashboard/costs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_events_page(client):
    resp = await client.get("/dashboard/events")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")

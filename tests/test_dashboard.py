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


@pytest.mark.asyncio
async def test_executive_page(client):
    resp = await client.get("/dashboard/executive")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_executive_page_with_data(client, session):
    from app.models.agent_run import AgentRun
    from datetime import datetime, timezone
    session.add(AgentRun(
        project_id="proj-e", agent_type="dev", agent_id="d1",
        success=True, duration_ms=100,
        executed_at=datetime.now(timezone.utc),
    ))
    session.add(AgentRun(
        project_id="proj-e", agent_type="dev", agent_id="d1",
        success=False, duration_ms=200,
        executed_at=datetime.now(timezone.utc),
    ))
    await session.flush()

    resp = await client.get("/dashboard/executive")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    body = resp.text
    assert "50" in body  # 50% success rate (1/2)

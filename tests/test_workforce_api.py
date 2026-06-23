import pytest


@pytest.mark.asyncio
async def test_workforce_summary_empty(client):
    resp = await client.get("/api/v1/workforce/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_agents"] >= 0


@pytest.mark.asyncio
async def test_register_agent(client):
    resp = await client.post("/api/v1/workforce/agents/developer/register")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_type"] == "developer"
    assert data["status"] == "idle"


@pytest.mark.asyncio
async def test_list_agents(client):
    await client.post("/api/v1/workforce/agents/developer/register")
    resp = await client.get("/api/v1/workforce/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 1


@pytest.mark.asyncio
async def test_get_agent(client):
    reg = await client.post("/api/v1/workforce/agents/developer/register")
    agent_id = reg.json()["agent_id"]

    resp = await client.get(f"/api/v1/workforce/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["agent_id"] == agent_id


@pytest.mark.asyncio
async def test_get_nonexistent_agent(client):
    resp = await client.get("/api/v1/workforce/agents/nonexistent")
    assert resp.status_code == 200
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_unregister_agent(client):
    reg = await client.post("/api/v1/workforce/agents/developer/register")
    agent_id = reg.json()["agent_id"]

    resp = await client.post(f"/api/v1/workforce/agents/{agent_id}/unregister")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_auto_register(client):
    resp = await client.post("/api/v1/workforce/auto-register")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_agents"] >= 5
    assert data["by_type"].get("developer", 0) >= 1
    assert data["by_type"].get("qa", 0) >= 1

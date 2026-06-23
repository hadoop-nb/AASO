import pytest


@pytest.mark.asyncio
async def test_list_events_empty(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Events Test", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{pid}/events")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_events_after_publish(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Events Test 2", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    from app.core.event_bus import Event, event_bus
    await event_bus.publish(Event(
        event_type="test.event",
        data={"project_id": pid, "msg": "hello"},
        source="test",
    ))

    resp = await client.get(f"/api/v1/projects/{pid}/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1


@pytest.mark.asyncio
async def test_replay_events_empty(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Replay Test", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    resp = await client.get(f"/api/v1/projects/{pid}/events/replay")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_event_stats(client):
    project_resp = await client.post("/api/v1/projects", json={
        "name": "Stats Test", "description": "T",
    })
    pid = project_resp.json()["project_id"]

    from app.core.event_bus import Event, event_bus
    await event_bus.publish(Event(
        event_type="stats.test",
        data={"project_id": pid},
        source="test",
    ))

    resp = await client.get(f"/api/v1/projects/{pid}/events/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert isinstance(stats, list)

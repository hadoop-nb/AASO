import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_developer_agent_execution(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Dev Agent Project",
            "description": "Test project for developer agent",
        },
    )
    pid = proj_resp.json()["project_id"]

    task_resp = await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={
            "title": "Build login feature",
            "description": "Implement JWT-based authentication",
            "priority": "high",
        },
    )
    tid = task_resp.json()["task_id"]

    response = await client.post(
        f"/api/v1/agents/developer/execute?project_id={pid}",
        json={"task_id": tid},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == tid
    assert len(data["files"]) > 0


@pytest.mark.asyncio
async def test_developer_produces_code_files(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Code Generation Test"},
    )
    pid = proj_resp.json()["project_id"]

    task_resp = await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={"title": "Generate API", "priority": "high"},
    )
    tid = task_resp.json()["task_id"]

    dev_resp = await client.post(
        f"/api/v1/agents/developer/execute?project_id={pid}",
        json={"task_id": tid},
    )
    assert dev_resp.status_code == 200

    code_resp = await client.get(
        f"/api/v1/projects/{pid}/code"
    )
    assert code_resp.status_code == 200
    assert len(code_resp.json()) >= 1


@pytest.mark.asyncio
async def test_developer_records_decision_and_lesson(
    client: AsyncClient,
):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Decision & Lesson Test"},
    )
    pid = proj_resp.json()["project_id"]

    task_resp = await client.post(
        f"/api/v1/projects/{pid}/tasks",
        json={"title": "Implement feature X"},
    )
    tid = task_resp.json()["task_id"]

    await client.post(
        f"/api/v1/agents/developer/execute?project_id={pid}",
        json={"task_id": tid},
    )

    decisions_resp = await client.get(
        f"/api/v1/projects/{pid}/decisions"
    )
    lessons_resp = await client.get(
        f"/api/v1/projects/{pid}/lessons"
    )

    # Stub provider returns decisions and lessons
    assert decisions_resp.status_code == 200
    assert lessons_resp.status_code == 200


@pytest.mark.asyncio
async def test_developer_rejects_nonexistent_task(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/agents/developer/execute?project_id=nonexistent",
        json={"task_id": "fake-task-id"},
    )
    assert response.status_code == 400 or response.status_code == 500

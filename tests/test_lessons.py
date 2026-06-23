import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_lesson(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "Lesson Project"}
    )
    pid = proj_resp.json()["project_id"]
    payload = {
        "problem": "Slow queries in production",
        "solution": "Added database indexes on foreign keys",
        "result": "Query time reduced by 90%",
    }
    response = await client.post(
        f"/api/v1/projects/{pid}/lessons", json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert "lesson_id" in data
    assert data["problem"] == "Slow queries in production"


@pytest.mark.asyncio
async def test_list_lessons(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects", json={"name": "List Lessons"}
    )
    pid = proj_resp.json()["project_id"]
    await client.post(
        f"/api/v1/projects/{pid}/lessons",
        json={
            "problem": "Bug in auth",
            "solution": "Fixed JWT validation",
            "result": "Working",
        },
    )
    response = await client.get(
        f"/api/v1/projects/{pid}/lessons"
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_cross_project_isolation(client: AsyncClient):
    p1 = await client.post(
        "/api/v1/projects", json={"name": "P1"}
    )
    p2 = await client.post(
        "/api/v1/projects", json={"name": "P2"}
    )
    pid1 = p1.json()["project_id"]
    pid2 = p2.json()["project_id"]

    await client.post(
        f"/api/v1/projects/{pid1}/lessons",
        json={
            "problem": "P1 issue",
            "solution": "Fixed",
            "result": "Done",
        },
    )

    lessons_p1 = await client.get(
        f"/api/v1/projects/{pid1}/lessons"
    )
    lessons_p2 = await client.get(
        f"/api/v1/projects/{pid2}/lessons"
    )

    assert len(lessons_p1.json()) == 1
    assert len(lessons_p2.json()) == 0

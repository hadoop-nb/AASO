import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_review_no_files(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Review Test"})
    pid = proj.json()["project_id"]
    resp = await client.post(
        f"/api/v1/projects/{pid}/review/execute",
        json={"task_id": "nonexistent", "file_ids": []},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_review_with_files(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "Review Files"})
    pid = proj.json()["project_id"]

    task = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Review Task"})
    tid = task.json()["task_id"]

    await client.post(
        f"/api/v1/projects/{pid}/code",
        json={
            "task_id": tid,
            "path": "src/app.py",
            "summary": "App module",
            "content": '"""App module."""\ndef run():\n    return "ok"\n',
            "language": "python",
        },
    )

    resp = await client.post(
        f"/api/v1/projects/{pid}/review/execute",
        json={"task_id": tid, "file_ids": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "approved" in data
    assert "score" in data
    assert "comments" in data

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_qa_validate_no_files(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "QA Test"})
    pid = proj.json()["project_id"]
    resp = await client.post(
        f"/api/v1/projects/{pid}/qa/validate",
        json={"task_id": "nonexistent", "file_ids": []},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_qa_validate_with_task_files(client: AsyncClient):
    proj = await client.post("/api/v1/projects", json={"name": "QA Files"})
    pid = proj.json()["project_id"]

    task = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "QA Task"})
    tid = task.json()["task_id"]

    await client.post(
        f"/api/v1/projects/{pid}/code",
        json={
            "task_id": tid,
            "path": "src/main.py",
            "summary": "Entry point",
            "content": "def main():\n    pass\n",
            "language": "python",
        },
    )

    resp = await client.post(
        f"/api/v1/projects/{pid}/qa/validate",
        json={"task_id": tid, "file_ids": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "passed" in data
    assert "summary" in data
    assert "qa_decision" in data

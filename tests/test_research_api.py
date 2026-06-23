from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analyze_code_endpoint(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Research Test", "description": "Test research API"},
    )
    pid = proj_resp.json()["project_id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/research/analyze-code",
        json={"code": "def foo(): pass\nclass Bar: pass", "language": "python"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "file_stats" in data
    assert data["structure"]["functions"] == ["foo"]
    assert data["structure"]["classes"] == ["Bar"]


@pytest.mark.asyncio
async def test_detect_stack_endpoint(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Stack Detection Test"},
    )
    pid = proj_resp.json()["project_id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/research/detect-stack",
        json={
            "files": [
                {"path": "requirements.txt", "content": "fastapi==0.104.0"},
                {"path": "Dockerfile", "content": "FROM python:3.11"},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "detected_technologies" in data
    assert data["file_count"] == 2


@pytest.mark.asyncio
async def test_check_dependencies_endpoint(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Deps Check Test"},
    )
    pid = proj_resp.json()["project_id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/research/check-dependencies",
        json={
            "files": [
                {
                    "path": "requirements.txt",
                    "content": "flask==2.3.0\nrequests==2.28.0",
                }
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "findings" in data
    assert data["total_dependencies"] >= 2


@pytest.mark.asyncio
async def test_recommend_technology_endpoint(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Tech Recommend Test"},
    )
    pid = proj_resp.json()["project_id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/research/recommend-technology",
        json={
            "requirement": "Build a real-time chat app",
            "context": "Node.js backend",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendation" in data


@pytest.mark.asyncio
async def test_code_review_endpoint(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Code Review Test"},
    )
    pid = proj_resp.json()["project_id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/research/code-review",
        json={
            "code": "def add(a, b): return a + b",
            "language": "python",
            "context": "simple utility",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_analyze_code_invalid_project(client: AsyncClient):
    resp = await client.post(
        "/api/v1/projects/invalid/research/analyze-code",
        json={"code": "x = 1", "language": "python"},
    )
    assert resp.status_code in (200, 500)


@pytest.mark.asyncio
async def test_research_endpoints_return_json(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "JSON Check Test"},
    )
    pid = proj_resp.json()["project_id"]

    endpoints = [
        ("/analyze-code", {"code": "x=1", "language": "python"}),
        ("/detect-stack", {"files": []}),
        ("/check-dependencies", {"files": []}),
        ("/recommend-technology", {"requirement": "test", "context": ""}),
        ("/code-review", {"code": "x=1", "language": "python", "context": ""}),
    ]

    for path, body in endpoints:
        resp = await client.post(
            f"/api/v1/projects/{pid}/research{path}", json=body
        )
        assert resp.status_code == 200, f"{path} failed: {resp.text}"
        content_type = resp.headers.get("content-type", "")
        assert "json" in content_type


@pytest.mark.asyncio
async def test_research_empty_code_analysis(client: AsyncClient):
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Empty Code Test"},
    )
    pid = proj_resp.json()["project_id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/research/analyze-code",
        json={"code": "", "language": "python"},
    )
    assert resp.status_code == 200
    assert resp.json()["file_stats"]["total_lines"] == 1

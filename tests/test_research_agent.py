from __future__ import annotations

import json

import pytest

from app.agents.base import AgentContext
from app.agents.research_agent import ResearchAgent
from app.services.llm_service import LLMProvider, LLMService


class _ResearchTestProvider(LLMProvider):
    def __init__(self, response: str | None = None):
        self.response = response

    async def generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        if self.response:
            return self.response

        if "architecture" in prompt or "code quality" in prompt:
            return json.dumps({
                "architecture": "Well-structured code",
                "quality": "Good practices followed",
                "improvements": ["Add type hints", "Add docstrings"],
                "security_notes": ["No security issues found"],
            })
        if "Requirement" in prompt and "recommend" in prompt.lower():
            return json.dumps({
                "recommendation": "FastAPI with SQLAlchemy",
                "alternatives": [
                    {
                        "name": "Django",
                        "pros": ["Batteries included", "Admin panel"],
                        "cons": ["Heavier", "More opinionated"],
                        "fit_score": 8,
                    }
                ],
                "reasoning": "Best for small team REST APIs",
            })
        if "Research and review" in prompt:
            return json.dumps({
                "best_practices": {"score": 8, "findings": ["Good naming"]},
                "design_patterns": ["Single Responsibility"],
                "performance": ["No bottlenecks detected"],
                "security": ["Input validation needed"],
                "testing_recommendations": ["Add unit tests"],
            })
        if "Review these project dependencies" in prompt:
            return json.dumps({
                "issues": [
                    {"package": "requests", "severity": "medium", "message": "Version 2.28.0 is outdated"}
                ],
                "recommendations": ["Upgrade requests to 2.31.0"],
            })
        if "identify the tech stack" in prompt.lower():
            return json.dumps({
                "primary_language": "Python",
                "framework": "FastAPI",
                "database": "PostgreSQL",
                "tools": ["Docker", "Git"],
                "confidence": 0.95,
            })

        return json.dumps({
            "plan": "Implementation plan generated.",
            "files": [],
            "decision": {},
            "lesson": {},
        })


@pytest.fixture
def agent():
    provider = _ResearchTestProvider()
    llm = LLMService(provider=provider)
    return ResearchAgent(
        context=AgentContext(
            agent_id="test-research",
            name="Test Research Agent",
            project_id="test-proj",
        ),
        llm=llm,
    )


@pytest.mark.asyncio
async def test_research_analyze_python_code(agent: ResearchAgent):
    code = '''
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

class Calculator:
    def add(self, a, b):
        return a + b
'''
    result = await agent.analyze_code(code, "python")
    assert "file_stats" in result
    assert result["file_stats"]["code_lines"] >= 4
    assert "greet" in result["structure"]["functions"]
    assert "Calculator" in result["structure"]["classes"]
    assert result["language"] == "python"


@pytest.mark.asyncio
async def test_research_analyze_java_code(agent: ResearchAgent):
    code = '''
public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}
'''
    result = await agent.analyze_code(code, "java")
    assert result["language"] == "java"
    assert "Hello" in result["structure"]["classes"]
    assert "main" in result["structure"]["functions"]


@pytest.mark.asyncio
async def test_research_detect_tech_stack(agent: ResearchAgent):
    files = [
        {"path": "requirements.txt", "content": "fastapi==0.104.0\nsqlalchemy==2.0.0"},
        {"path": "Dockerfile", "content": "FROM python:3.11"},
        {"path": "src/main.py", "content": "from fastapi import FastAPI"},
    ]
    result = await agent.detect_tech_stack(files)
    assert "detected_technologies" in result
    assert len(result["detected_technologies"]) >= 3
    assert "fastapi" in result["detected_technologies"]
    assert result["file_count"] == 3


@pytest.mark.asyncio
async def test_research_detect_stack_no_files(agent: ResearchAgent):
    result = await agent.detect_tech_stack([])
    assert result["file_count"] == 0
    assert isinstance(result["detected_technologies"], list)


@pytest.mark.asyncio
async def test_research_check_dependencies(agent: ResearchAgent):
    files = [
        {
            "path": "requirements.txt",
            "content": "requests==2.28.0\nflask==2.3.0\n",
        },
    ]
    result = await agent.check_dependencies(files, project_id="proj-1")
    assert "findings" in result
    assert any(d["package"] == "requests" for d in result["findings"])
    assert any(d["package"] == "flask" for d in result["findings"])
    assert result["total_dependencies"] >= 2


@pytest.mark.asyncio
async def test_research_check_dependencies_no_dep_files(agent: ResearchAgent):
    files = [{"path": "main.py", "content": "print('hello')"}]
    result = await agent.check_dependencies(files, project_id="proj-1")
    assert result["total_dependencies"] == 0


@pytest.mark.asyncio
async def test_research_recommend_technology(agent: ResearchAgent):
    result = await agent.recommend_technology(
        requirement="Build a REST API with Python",
        context="Small team, need quick development",
    )
    assert "recommendation" in result
    assert result["recommendation"]


@pytest.mark.asyncio
async def test_research_code_review_basic(agent: ResearchAgent):
    code = '''
def risky_function(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result
'''
    result = await agent.research_code_review(code, "python", "simple example")
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_research_execute_analyze_code(agent: ResearchAgent):
    result = await agent.execute({
        "action": "analyze_code",
        "code": "def foo(): pass",
        "language": "python",
    })
    assert "file_stats" in result
    assert result["structure"]["functions"] == ["foo"]


@pytest.mark.asyncio
async def test_research_execute_detect_stack(agent: ResearchAgent):
    result = await agent.execute({
        "action": "detect_stack",
        "files": [{"path": "package.json", "content": "{}"}],
    })
    assert "detected_technologies" in result


@pytest.mark.asyncio
async def test_research_execute_check_deps(agent: ResearchAgent):
    result = await agent.execute({
        "action": "check_dependencies",
        "files": [{"path": "Cargo.toml", "content": "[dependencies]\nserde = \"1.0\""}],
    })
    assert "findings" in result


@pytest.mark.asyncio
async def test_research_execute_recommend(agent: ResearchAgent):
    result = await agent.execute({
        "action": "recommend_tech",
        "requirement": "Database for analytics",
    })
    assert "recommendation" in result


@pytest.mark.asyncio
async def test_research_execute_code_review(agent: ResearchAgent):
    result = await agent.execute({
        "action": "code_review",
        "code": "x = 1",
        "language": "python",
    })
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_research_unknown_action(agent: ResearchAgent):
    result = await agent.execute({"action": "nonexistent"})
    assert "error" in result


@pytest.mark.asyncio
async def test_research_protocol_registered(agent: ResearchAgent):
    from app.core.agent_protocol import agent_registry

    cap = agent_registry.find_by_id(agent.agent_id)
    assert cap is not None
    assert "research.analyze_code" in cap.protocols
    assert "research.detect_stack" in cap.protocols
    assert "research.dependency_check" in cap.protocols
    assert "research.tech_recommend" in cap.protocols
    assert "research.code_review" in cap.protocols


@pytest.mark.asyncio
async def test_research_protocol_message_handling(agent: ResearchAgent):
    from app.core.agent_protocol import AgentMessage, message_router

    msg = AgentMessage(
        message_id="test-msg",
        protocol="research.analyze_code",
        payload={"code": "def foo(): pass", "language": "python"},
        source_agent="tester",
        target_agent=agent.agent_id,
        correlation_id="corr-1",
    )
    result = await message_router.request(
        target_agent=agent.agent_id,
        protocol="research.analyze_code",
        payload={"code": "def foo(): pass", "language": "python"},
        source_agent="tester",
        timeout=5,
    )
    assert "file_stats" in result
    assert result["structure"]["functions"] == ["foo"]


@pytest.mark.asyncio
async def test_research_protocol_unknown_protocol(agent: ResearchAgent):
    from app.core.agent_protocol import AgentMessage, message_router

    msg = AgentMessage(
        message_id="unknown-msg",
        protocol="research.nonexistent",
        payload={},
        source_agent="tester",
        target_agent=agent.agent_id,
    )
    result = await message_router.request(
        target_agent=agent.agent_id,
        protocol="research.nonexistent",
        payload={},
        source_agent="tester",
        timeout=5,
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_research_empty_code(agent: ResearchAgent):
    result = await agent.analyze_code("", "python")
    assert result["file_stats"]["total_lines"] == 1


@pytest.mark.asyncio
async def test_research_large_code_batch(agent: ResearchAgent):
    lines = []
    for i in range(100):
        lines.append(f"def func_{i}(): pass")
    code = "\n".join(lines)

    result = await agent.analyze_code(code, "python")
    assert len(result["structure"]["functions"]) >= 50


@pytest.mark.asyncio
async def test_research_agent_reuses_registry(agent: ResearchAgent):
    from app.core.agent_protocol import agent_registry

    agent2 = ResearchAgent(
        context=AgentContext(
            agent_id="test-research-2",
            name="Test Research Agent 2",
            project_id="test-proj",
        ),
    )

    cap1 = agent_registry.find_by_id(agent.agent_id)
    cap2 = agent_registry.find_by_id(agent2.agent_id)
    assert cap1 is not None
    assert cap2 is not None
    assert cap1.agent_id != cap2.agent_id

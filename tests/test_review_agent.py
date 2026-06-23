import pytest

from app.agents.base import AgentContext
from app.agents.review_agent import ReviewAgent


@pytest.fixture
def agent():
    return ReviewAgent(
        context=AgentContext(
            agent_id="review-001",
            name="Review Agent",
            project_id="p1",
        )
    )


@pytest.mark.asyncio
async def test_review_empty_list(agent: ReviewAgent):
    result = await agent.review_code([], task_context="test")
    assert result["approved"] is False
    assert result["score"] == 0.0


@pytest.mark.asyncio
async def test_review_good_code(agent: ReviewAgent):
    files = [
        {"path": "src/main.py", "content": '"""Module docstring."""\ndef main():\n    print("hello")\n', "language": "python"},
    ]
    result = await agent.review_code(files, task_context="test task")
    assert "approved" in result
    assert "score" in result
    assert "comments" in result
    assert "summary" in result


@pytest.mark.asyncio
async def test_review_long_file_penalty(agent: ReviewAgent):
    lines = [f"print({i})" for i in range(350)]
    content = "\n".join(lines)
    files = [{"path": "src/long.py", "content": content, "language": "python"}]
    result = await agent.review_code(files, task_context="")
    long_line_comments = [c for c in result["comments"] if "lines" in c.get("message", "").lower()]
    assert len(long_line_comments) >= 1


@pytest.mark.asyncio
async def test_review_with_qa_context(agent: ReviewAgent):
    files = [{"path": "src/main.py", "content": "x = 1\n", "language": "python"}]
    qa_result = {"passed": True, "summary": "All good"}
    result = await agent.review_code(files, qa_results=qa_result, task_context="impl x")
    assert result["summary"] is not None

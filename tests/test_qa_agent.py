import pytest

from app.agents.base import AgentContext
from app.agents.qa_agent import QAAgent


@pytest.fixture
def agent():
    return QAAgent(
        context=AgentContext(
            agent_id="qa-001",
            name="QA Agent",
            project_id="p1",
        )
    )


@pytest.mark.asyncio
async def test_validate_empty_file(agent: QAAgent):
    files = [{"path": "src/empty.py", "content": "", "language": "python"}]
    result = await agent.validate_code(files, "")
    assert result["passed"] is False
    assert result["qa_decision"] == "changes_requested"
    assert any("empty" in i["message"].lower() for r in result["files"] for i in r.get("issues", []))


@pytest.mark.asyncio
async def test_validate_good_file(agent: QAAgent):
    files = [{"path": "src/main.py", "content": "def main():\n    pass\n", "language": "python"}]
    result = await agent.validate_code(files, "")
    assert "passed" in result
    assert "summary" in result


@pytest.mark.asyncio
async def test_validate_multiple_files(agent: QAAgent):
    files = [
        {"path": "src/a.py", "content": "x = 1\n", "language": "python"},
        {"path": "src/b.py", "content": "", "language": "python"},
    ]
    result = await agent.validate_code(files, "")
    assert len(result["files"]) == 2
    assert result["files"][1]["passed"] is False


@pytest.mark.asyncio
async def test_detect_trailing_whitespace(agent: QAAgent):
    content = "def foo():\n    pass \n"
    files = [{"path": "src/test.py", "content": content, "language": "python"}]
    result = await agent.validate_code(files, "")
    file_result = result["files"][0]
    whitespace_issues = [i for i in file_result.get("issues", []) if "whitespace" in i.get("message", "").lower()]
    assert len(whitespace_issues) >= 1

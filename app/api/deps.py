from collections.abc import AsyncGenerator

from fastapi import Depends
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.developer import DeveloperAgent
from app.agents.qa_agent import QAAgent
from app.agents.review_agent import ReviewAgent
from app.agents.base import AgentContext
from app.core.database import get_db
from app.core.memory import get_qdrant
from app.services.code_service import CodeService
from app.services.decision_service import DecisionService
from app.services.lesson_service import LessonService
from app.services.memory_service import MemoryService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


async def get_project_service(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[ProjectService, None]:
    yield ProjectService(session)


async def get_task_service(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[TaskService, None]:
    yield TaskService(session)


async def get_decision_service(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[DecisionService, None]:
    yield DecisionService(session)


async def get_lesson_service(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[LessonService, None]:
    yield LessonService(session)


async def get_memory_service(
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
) -> AsyncGenerator[MemoryService, None]:
    yield MemoryService(qdrant)


async def get_code_service(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[CodeService, None]:
    yield CodeService(session)


def get_workflow_handlers(
    session: AsyncSession,
    memory: MemoryService | None = None,
) -> dict:
    from app.services.analytics_service import analytics_service
    from app.services.developer_service import DeveloperService

    async def developer_handler(**kwargs) -> dict:
        context = kwargs.get("context", {})
        dev_service = DeveloperService(session, memory)
        result = await dev_service.execute_task(
            project_id=context.get("project_id", ""),
            task_id=context.get("task_id", ""),
        )
        analytics_service.record_run(
            AgentContext(
                agent_id="dev-001",
                name="Developer Agent",
                project_id=context.get("project_id", ""),
                task_id=context.get("task_id", ""),
            )
        )
        return result

    async def qa_handler(**kwargs) -> dict:
        context = kwargs.get("context", {})
        files = kwargs.get("developer", {}).get("files", [])
        agent = QAAgent(
            context=AgentContext(
                agent_id="qa-001",
                name="QA Agent",
                project_id=context.get("project_id", ""),
                task_id=context.get("task_id", ""),
            ),
        )
        files_data = []
        for fid in files:
            f = await CodeService(session).get(fid)
            if f:
                files_data.append({"path": f.path, "content": f.content, "language": f.language})
        return await agent.validate_code(files_data, task_context=str(context))

    async def review_handler(**kwargs) -> dict:
        context = kwargs.get("context", {})
        files = kwargs.get("developer", {}).get("files", [])
        qa_result = kwargs.get("qa", {})
        agent = ReviewAgent(
            context=AgentContext(
                agent_id="review-001",
                name="Review Agent",
                project_id=context.get("project_id", ""),
                task_id=context.get("task_id", ""),
            ),
        )
        files_data = []
        for fid in files:
            f = await CodeService(session).get(fid)
            if f:
                files_data.append({"path": f.path, "content": f.content, "language": f.language})
        return await agent.review_code(files_data, qa_results=qa_result, task_context=str(context))

    return {
        "developer": developer_handler,
        "qa": qa_handler,
        "review": review_handler,
    }

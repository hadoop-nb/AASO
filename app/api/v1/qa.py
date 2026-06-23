from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.qa_agent import QAAgent
from app.core.database import get_db
from app.services.code_service import CodeService

router = APIRouter(prefix="/projects/{project_id}/qa")


class QARequest(BaseModel):
    task_id: str
    file_ids: list[str] = []


class QAResponse(BaseModel):
    passed: bool
    summary: str
    qa_decision: str


@router.post("/validate")
async def validate_code(
    project_id: str,
    request: QARequest,
    session: AsyncSession = Depends(get_db),
):
    code_service = CodeService(session)
    files = []
    if request.file_ids:
        for fid in request.file_ids:
            f = await code_service.get(fid)
            if f and f.project_id == project_id:
                files.append({
                    "path": f.path,
                    "content": f.content,
                    "language": f.language,
                })
    else:
        all_files = await code_service.list_by_project(project_id)
        task_files = [f for f in all_files if f.task_id == request.task_id]
        files = [
            {"path": f.path, "content": f.content, "language": f.language}
            for f in task_files
        ]

    if not files:
        raise HTTPException(status_code=404, detail="No files found to validate")

    agent = QAAgent(
        context=AgentContext(
            agent_id="qa-001",
            name="QA Agent",
            project_id=project_id,
            task_id=request.task_id,
        ),
    )
    result = await agent.validate_code(files, task_context=f"Task: {request.task_id}")
    return QAResponse(
        passed=result["passed"],
        summary=result["summary"],
        qa_decision=result["qa_decision"],
    )

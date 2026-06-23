from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.review_agent import ReviewAgent
from app.core.database import get_db
from app.services.code_service import CodeService

router = APIRouter(prefix="/projects/{project_id}/review")


class ReviewRequest(BaseModel):
    task_id: str
    file_ids: list[str] = []


@router.post("/execute")
async def execute_review(
    project_id: str,
    request: ReviewRequest,
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
        raise HTTPException(status_code=404, detail="No files found to review")

    agent = ReviewAgent(
        context=AgentContext(
            agent_id="review-001",
            name="Review Agent",
            project_id=project_id,
            task_id=request.task_id,
        ),
    )
    result = await agent.review_code(
        files,
        task_context=f"Task: {request.task_id}",
    )
    return result

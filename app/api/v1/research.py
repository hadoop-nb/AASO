from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.llm_service import llm_service
from app.services.research_service import ResearchService

router = APIRouter(prefix="/projects/{project_id}/research")


class AnalyzeCodeRequest(BaseModel):
    code: str
    language: str = "python"


class DetectStackRequest(BaseModel):
    files: list[dict]


class DependencyCheckRequest(BaseModel):
    files: list[dict]


class TechRecommendRequest(BaseModel):
    requirement: str
    context: str = ""


class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"
    context: str = ""


def _get_service() -> ResearchService:
    return ResearchService(llm=llm_service)


@router.post("/analyze-code")
async def analyze_code(
    project_id: str,
    request: AnalyzeCodeRequest,
):
    try:
        service = _get_service()
        return await service.analyze_code(project_id, request.code, request.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-stack")
async def detect_tech_stack(
    project_id: str,
    request: DetectStackRequest,
):
    try:
        service = _get_service()
        return await service.detect_tech_stack(project_id, request.files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-dependencies")
async def check_dependencies(
    project_id: str,
    request: DependencyCheckRequest,
):
    try:
        service = _get_service()
        return await service.check_dependencies(project_id, request.files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend-technology")
async def recommend_technology(
    project_id: str,
    request: TechRecommendRequest,
):
    try:
        service = _get_service()
        return await service.recommend_technology(
            project_id, request.requirement, request.context
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code-review")
async def research_code_review(
    project_id: str,
    request: CodeReviewRequest,
):
    try:
        service = _get_service()
        return await service.research_code_review(
            project_id, request.code, request.language, request.context
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

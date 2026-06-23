from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_lesson_service, get_memory_service
from app.schemas.lesson import LessonCreate, LessonResponse
from app.services.lesson_service import LessonService
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/projects/{project_id}/lessons")


@router.post("", response_model=LessonResponse, status_code=201)
async def create_lesson(
    project_id: str,
    data: LessonCreate,
    lesson_service: LessonService = Depends(get_lesson_service),
    memory_service: MemoryService = Depends(get_memory_service),
):
    lesson = await lesson_service.create(project_id, data)
    await memory_service.index_entity(
        entity_type="lesson",
        entity_id=lesson.lesson_id,
        project_id=project_id,
        content=f"Problem: {data.problem}\nSolution: {data.solution}\nResult: {data.result}",
    )
    return lesson


@router.get("", response_model=list[LessonResponse])
async def list_lessons(
    project_id: str,
    service: LessonService = Depends(get_lesson_service),
):
    return await service.list_by_project(project_id)


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    project_id: str,
    lesson_id: str,
    service: LessonService = Depends(get_lesson_service),
):
    lesson = await service.get(lesson_id)
    if not lesson or lesson.project_id != project_id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson

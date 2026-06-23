from datetime import datetime

from pydantic import BaseModel, Field


class LessonCreate(BaseModel):
    problem: str = Field(..., min_length=1)
    solution: str = Field(..., min_length=1)
    result: str = ""


class LessonResponse(BaseModel):
    lesson_id: str
    project_id: str
    problem: str
    solution: str
    result: str
    created_at: datetime

    model_config = {"from_attributes": True}

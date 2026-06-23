from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    project_id: str
    name: str
    status: str
    total_tasks: int
    completed_tasks: int
    completion_percentage: float
    total_decisions: int
    total_lessons: int


class ProgressReport(BaseModel):
    project_id: str
    name: str
    status: str
    task_breakdown: dict[str, int]
    completion_percentage: float
    recent_decisions: list[dict]
    recent_lessons: list[dict]

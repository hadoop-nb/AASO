from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    completion_percentage: int | None = Field(None, ge=0, le=100)


class TaskResponse(BaseModel):
    task_id: str
    project_id: str
    title: str
    description: str
    status: str
    priority: str
    completion_percentage: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

from datetime import datetime

from pydantic import BaseModel, Field


class CodeFileCreate(BaseModel):
    path: str = Field(..., min_length=1)
    summary: str = ""
    content: str = ""
    language: str = ""
    task_id: str | None = None


class CodeFileResponse(BaseModel):
    file_id: str
    project_id: str
    task_id: str | None
    path: str
    summary: str
    content: str
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}

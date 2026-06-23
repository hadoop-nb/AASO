from datetime import datetime

from pydantic import BaseModel, Field


class MemoryQuery(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=50)
    filter_types: list[str] | None = None


class MemoryResult(BaseModel):
    entity_type: str
    entity_id: str
    content: str
    score: float
    created_at: datetime

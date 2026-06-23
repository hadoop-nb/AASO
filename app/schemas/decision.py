from datetime import datetime

from pydantic import BaseModel, Field


class DecisionCreate(BaseModel):
    question: str = Field(..., min_length=1)
    alternatives: list[str] = []
    selected: str = Field(..., min_length=1)
    reason: str = ""


class DecisionResponse(BaseModel):
    decision_id: str
    project_id: str
    question: str
    alternatives: list[str]
    selected: str
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}

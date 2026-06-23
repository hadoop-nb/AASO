from __future__ import annotations

PROJECT_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "created": ["in_progress"],
    "in_progress": ["blocked", "completed"],
    "blocked": ["in_progress"],
    "completed": ["archived"],
    "archived": [],
}

TASK_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["in_progress"],
    "in_progress": ["completed", "failed"],
    "completed": [],
    "failed": ["in_progress"],
}


def validate_project_transition(current: str, next_status: str) -> bool:
    return next_status in PROJECT_STATUS_TRANSITIONS.get(current, [])


def validate_task_transition(current: str, next_status: str) -> bool:
    return next_status in TASK_STATUS_TRANSITIONS.get(current, [])

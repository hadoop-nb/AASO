from collections.abc import MutableMapping

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db


class PassthroughCache(MutableMapping):
    def __getitem__(self, key): raise KeyError(key)
    def __setitem__(self, key, value): pass
    def __delitem__(self, key): pass
    def __iter__(self): return iter([])
    def __len__(self): return 0
from app.models.project import Project
from app.models.task import Task
from app.models.agent_run import AgentRun
from app.models.lesson import Lesson
from app.models.decision import Decision
from app.services.cost_tracker import cost_tracker as default_tracker
from app.services.workforce_service import workforce_service as default_ws
from app.core.event_bus import event_bus

templates = Jinja2Templates(directory="app/templates")
templates.env.cache = PassthroughCache()
router = APIRouter()


@router.get("/dashboard")
async def overview(request: Request, session: AsyncSession = Depends(get_db)):
    project_count = await session.scalar(select(func.count(Project.project_id)))
    task_count = await session.scalar(select(func.count(Task.task_id)))
    agent_run_count = await session.scalar(select(func.count(AgentRun.run_id)))

    result = await session.execute(
        select(Project).order_by(Project.created_at.desc()).limit(10)
    )
    projects = result.scalars().all()

    project_list = []
    for p in projects:
        tc = await session.scalar(
            select(func.count(Task.task_id)).where(Task.project_id == p.project_id)
        )
        project_list.append({
            "project_id": p.project_id,
            "name": p.name,
            "status": p.status or "active",
            "task_count": tc or 0,
            "created_at": p.created_at.isoformat() if p.created_at else "",
        })

    ws = default_ws
    pool = ws.get_pool_summary() if ws.list_agents() else None

    return templates.TemplateResponse(
        request,
        "overview.html",
        {
            "active": "overview",
            "stats": {
                "project_count": project_count or 0,
                "task_count": task_count or 0,
                "agent_run_count": agent_run_count or 0,
                "workforce_size": (pool or {}).get("total_agents", 0),
            },
            "projects": project_list,
            "pool": pool,
        },
    )


@router.get("/dashboard/projects")
async def project_list(request: Request, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    project_list = []
    for p in projects:
        tc = await session.scalar(
            select(func.count(Task.task_id)).where(Task.project_id == p.project_id)
        )
        project_list.append({
            "project_id": p.project_id,
            "name": p.name,
            "description": p.description,
            "status": p.status or "active",
            "task_count": tc or 0,
            "created_at": p.created_at.isoformat() if p.created_at else "",
        })

    return templates.TemplateResponse(
        request,
        "projects.html",
        {"active": "projects", "projects": project_list},
    )


@router.get("/dashboard/projects/{project_id}")
async def project_detail(
    request: Request, project_id: str, session: AsyncSession = Depends(get_db)
):
    project = await session.get(Project, project_id)
    if not project:
        return templates.TemplateResponse(
            request,
            "projects.html",
            {"active": "projects", "projects": []},
        )

    task_result = await session.execute(
        select(Task).where(Task.project_id == project_id)
    )
    tasks = [
        {
            "title": t.title,
            "status": t.status or "pending",
            "priority": t.priority or "medium",
            "completion_percentage": t.completion_percentage or 0,
        }
        for t in task_result.scalars().all()
    ]

    decision_result = await session.execute(
        select(Decision).where(Decision.project_id == project_id)
    )
    decisions = [
        {
            "question": d.question,
            "selected": d.selected or "",
        }
        for d in decision_result.scalars().all()
    ]

    lesson_result = await session.execute(
        select(Lesson).where(Lesson.project_id == project_id)
    )
    lessons = [
        {
            "problem": l.problem,
            "solution": l.solution,
        }
        for l in lesson_result.scalars().all()
    ]

    return templates.TemplateResponse(
        request,
        "project_detail.html",
        {
            "active": "projects",
            "project": project,
            "tasks": tasks,
            "decisions": decisions,
            "lessons": lessons,
        },
    )


@router.get("/dashboard/workforce")
async def workforce(request: Request):
    ws = default_ws
    pool = ws.get_pool_summary()
    return templates.TemplateResponse(
        request,
        "workforce.html",
        {"active": "workforce", "pool": pool},
    )


@router.get("/dashboard/costs")
async def costs(request: Request, session: AsyncSession = Depends(get_db)):
    tracker = default_tracker
    tracker.set_session(session)
    stats = await tracker.get_overall_stats()
    by_model = await tracker.get_cost_by_model()
    return templates.TemplateResponse(
        request,
        "costs.html",
        {
            "active": "costs",
            "stats": stats,
            "by_model": by_model,
        },
    )


@router.get("/dashboard/events")
async def events(request: Request):
    history = await event_bus.get_history(limit=50)
    event_list = [
        {
            "event_type": e.event_type,
            "source": e.source,
            "data": str(e.data)[:120],
            "timestamp": e.timestamp.isoformat(),
        }
        for e in history
    ]
    return templates.TemplateResponse(
        request,
        "events.html",
        {"active": "events", "events": event_list},
    )

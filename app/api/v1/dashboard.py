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


def _health_score(success_rate: float, cost_eff: float, assessment_avg: float | None) -> float:
    score = 0.0
    score += min(success_rate / 100, 1.0) * 40
    score += min(cost_eff, 1.0) * 20
    score += (min(assessment_avg or 5.0, 10.0) / 10.0) * 40 if assessment_avg is not None else 20
    return round(score, 0)


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


@router.get("/dashboard/executive")
async def executive(request: Request, session: AsyncSession = Depends(get_db)):
    from app.models.agent_run import AgentRun
    from app.models.project import Project
    from app.models.task import Task
    from app.models.prompt_template import AgentAssessment
    from app.services.cost_tracker import cost_tracker as default_tracker
    from sqlalchemy import case, Integer

    project_count = await session.scalar(select(func.count(Project.project_id)))
    task_count = await session.scalar(select(func.count(Task.task_id)))

    run_result = await session.execute(
        select(
            func.count(AgentRun.run_id).label("total"),
            func.sum(case((AgentRun.success == True, 1), else_=0).cast(Integer)).label("successful"),
        )
    )
    run_row = run_result.one()
    total_runs = run_row.total or 0
    successful = run_row.successful or 0
    success_rate = (successful / total_runs * 100) if total_runs > 0 else 0

    tracker = default_tracker
    tracker.set_session(session)
    cost_stats = await tracker.get_overall_stats()
    cost_per_run = cost_stats["total_cost_usd"] / total_runs if total_runs > 0 else 0
    cost_eff = max(0, 1.0 - (cost_per_run / 0.01))

    assessment_result = await session.execute(
        select(func.avg(AgentAssessment.score))
    )
    avg_assessment = assessment_result.scalar()

    health = _health_score(success_rate, cost_eff, avg_assessment)

    result = await session.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    project_health = []
    for p in projects:
        pr = await session.execute(
            select(
                func.count(AgentRun.run_id).label("total"),
                func.sum(case((AgentRun.success == True, 1), else_=0).cast(Integer)).label("ok"),
            ).where(AgentRun.project_id == p.project_id)
        )
        pr_row = pr.one()
        p_total = pr_row.total or 0
        p_ok = pr_row.ok or 0
        p_rate = (p_ok / p_total * 100) if p_total > 0 else 0
        project_health.append({
            "name": p.name or p.project_id[:8],
            "project_id": p.project_id,
            "runs": p_total,
            "success_rate": round(p_rate, 0),
        })

    project_health.sort(key=lambda x: x["success_rate"])

    return templates.TemplateResponse(
        request,
        "executive.html",
        {
            "active": "executive",
            "health": health,
            "project_count": project_count or 0,
            "task_count": task_count or 0,
            "total_runs": total_runs,
            "success_rate": round(success_rate, 0),
            "cost_per_run": round(cost_per_run, 6),
            "avg_assessment": round(avg_assessment, 1) if avg_assessment else None,
            "project_health": project_health,
        },
    )

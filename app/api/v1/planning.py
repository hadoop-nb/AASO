from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.planning_service import PlanningService

router = APIRouter(prefix="/plans")


@router.post("")
async def create_plan(
    project_id: str,
    goal: str,
    priority: str = Query("medium"),
    notes: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    plan = await svc.create_plan(project_id, goal, priority, notes)
    return {"plan_id": plan.plan_id, "goal": plan.goal, "status": plan.status}


@router.get("")
async def list_plans(
    project_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    return await svc.list_plans(project_id, limit, offset)


@router.get("/{plan_id}")
async def get_plan(
    plan_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    plan = await svc.get_plan(plan_id)
    if not plan:
        return {"error": "Plan not found", "plan_id": plan_id}
    return plan


@router.patch("/{plan_id}/status")
async def update_plan_status(
    plan_id: str,
    status: str,
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    plan = await svc.update_plan_status(plan_id, status)
    if not plan:
        return {"error": "Plan not found", "plan_id": plan_id}
    return plan


@router.post("/{plan_id}/tasks")
async def add_plan_task(
    plan_id: str,
    title: str,
    description: str | None = None,
    priority: str = Query("medium"),
    estimated_hours: float | None = None,
    dependencies: str | None = None,
    assigned_agent_type: str | None = None,
    parent_task_id: str | None = None,
    sort_order: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    dep_list = dependencies.split(",") if dependencies else None
    task = await svc.add_plan_task(
        plan_id, title, description, priority,
        estimated_hours, dep_list, assigned_agent_type,
        parent_task_id, sort_order,
    )
    return {"task_id": task.task_id, "title": task.title}


@router.get("/{plan_id}/tasks")
async def get_plan_tasks(
    plan_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    return await svc.get_plan_tasks(plan_id)


@router.patch("/tasks/{task_id}")
async def update_plan_task(
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    risk_score: float | None = None,
    risk_factors: str | None = None,
    estimated_hours: float | None = None,
    dependencies: str | None = None,
    assigned_agent_type: str | None = None,
    sort_order: int | None = None,
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    dep_list = dependencies.split(",") if dependencies else None
    rf_list = risk_factors.split(",") if risk_factors else None
    task = await svc.update_plan_task(
        task_id, title, description, status, priority,
        risk_score, rf_list, estimated_hours, dep_list,
        assigned_agent_type, sort_order,
    )
    if not task:
        return {"error": "Task not found", "task_id": task_id}
    return task


@router.delete("/tasks/{task_id}")
async def delete_plan_task(
    task_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    deleted = await svc.delete_plan_task(task_id)
    return {"deleted": deleted, "task_id": task_id}


@router.get("/{plan_id}/risk-analysis")
async def analyze_risks(
    plan_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    return await svc.analyze_risks(plan_id)


@router.get("/{plan_id}/prioritized-tasks")
async def prioritized_tasks(
    plan_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    return await svc.prioritize_tasks(plan_id)


@router.post("/work-breakdown")
async def work_breakdown(
    goal: str,
    project_id: str,
    priority: str = Query("medium"),
    session: AsyncSession = Depends(get_db),
):
    svc = PlanningService(session)
    return await svc.work_breakdown(goal, project_id, priority)

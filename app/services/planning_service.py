from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import PlanTask, ProjectPlan
from app.repositories.plan_repo import PlanTaskRepository, ProjectPlanRepository

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
PRIORITIES = ("low", "medium", "high", "critical")
STATUSES = ("draft", "active", "completed", "cancelled")
TASK_STATUSES = ("pending", "in_progress", "completed", "blocked")


class PlanningService:
    def __init__(self, session: AsyncSession):
        self._plan_repo = ProjectPlanRepository(session)
        self._task_repo = PlanTaskRepository(session)
        self._session = session

    async def create_plan(
        self,
        project_id: str,
        goal: str,
        priority: str = "medium",
        notes: str | None = None,
    ) -> ProjectPlan:
        if priority not in PRIORITIES:
            raise ValueError(f"Priority must be one of {PRIORITIES}")

        return await self._plan_repo.create({
            "project_id": project_id,
            "goal": goal,
            "status": "draft",
            "priority": priority,
            "notes": notes,
        })

    async def get_plan(self, plan_id: str) -> dict | None:
        plan = await self._plan_repo.get(plan_id)
        return self._plan_to_dict(plan) if plan else None

    async def list_plans(
        self, project_id: str, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        plans = await self._plan_repo.list_by_project(project_id, limit, offset)
        return [self._plan_to_dict(p) for p in plans]

    async def update_plan_status(
        self, plan_id: str, status: str
    ) -> dict | None:
        if status not in STATUSES:
            raise ValueError(f"Status must be one of {STATUSES}")

        plan = await self._plan_repo.update(plan_id, {"status": status})
        return self._plan_to_dict(plan) if plan else None

    async def add_plan_task(
        self,
        plan_id: str,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        estimated_hours: float | None = None,
        dependencies: list[str] | None = None,
        assigned_agent_type: str | None = None,
        parent_task_id: str | None = None,
        sort_order: int = 0,
    ) -> PlanTask:
        plan = await self._plan_repo.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        if priority not in PRIORITIES:
            raise ValueError(f"Priority must be one of {PRIORITIES}")

        return await self._task_repo.create({
            "plan_id": plan_id,
            "parent_task_id": parent_task_id,
            "title": title,
            "description": description,
            "status": "pending",
            "priority": priority,
            "estimated_hours": estimated_hours,
            "dependencies": json.dumps(dependencies or []),
            "assigned_agent_type": assigned_agent_type,
            "sort_order": sort_order,
        })

    async def update_plan_task(
        self,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        risk_score: float | None = None,
        risk_factors: list[str] | None = None,
        estimated_hours: float | None = None,
        dependencies: list[str] | None = None,
        assigned_agent_type: str | None = None,
        sort_order: int | None = None,
    ) -> dict | None:
        task = await self._task_repo.get(task_id)
        if not task:
            return None

        if status is not None and status not in TASK_STATUSES:
            raise ValueError(f"Status must be one of {TASK_STATUSES}")
        if priority is not None and priority not in PRIORITIES:
            raise ValueError(f"Priority must be one of {PRIORITIES}")

        data: dict = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if status is not None:
            data["status"] = status
        if priority is not None:
            data["priority"] = priority
        if risk_score is not None:
            data["risk_score"] = risk_score
        if risk_factors is not None:
            data["risk_factors"] = json.dumps(risk_factors)
        if estimated_hours is not None:
            data["estimated_hours"] = estimated_hours
        if dependencies is not None:
            data["dependencies"] = json.dumps(dependencies)
        if assigned_agent_type is not None:
            data["assigned_agent_type"] = assigned_agent_type
        if sort_order is not None:
            data["sort_order"] = sort_order

        updated = await self._task_repo.update(task_id, data)
        return self._task_to_dict(updated) if updated else None

    async def delete_plan_task(self, task_id: str) -> bool:
        return await self._task_repo.delete(task_id)

    async def get_plan_tasks(self, plan_id: str) -> list[dict]:
        tasks = await self._task_repo.list_by_plan(plan_id)
        return [self._task_to_dict(t) for t in tasks]

    async def analyze_risks(self, plan_id: str) -> dict:
        tasks = await self._task_repo.list_by_plan(plan_id)
        if not tasks:
            return {"plan_id": plan_id, "overall_risk": None, "high_risk_tasks": []}

        scored_tasks = [
            t for t in tasks if t.risk_score is not None
        ]
        high_risk = [t for t in scored_tasks if t.risk_score >= 0.7]
        medium_risk = [t for t in scored_tasks if 0.4 <= t.risk_score < 0.7]

        overall = (
            sum(t.risk_score for t in scored_tasks) / len(scored_tasks)
            if scored_tasks
            else None
        )

        return {
            "plan_id": plan_id,
            "overall_risk": round(overall, 2) if overall is not None else None,
            "total_tasks": len(tasks),
            "scored_tasks": len(scored_tasks),
            "high_risk_count": len(high_risk),
            "medium_risk_count": len(medium_risk),
            "high_risk_tasks": [self._task_to_dict(t) for t in high_risk],
            "medium_risk_tasks": [self._task_to_dict(t) for t in medium_risk],
        }

    async def prioritize_tasks(self, plan_id: str) -> list[dict]:
        tasks = await self._task_repo.list_by_plan(plan_id)
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (
                PRIORITY_ORDER.get(t.priority, 99),
                t.sort_order or 0,
            ),
        )
        return [self._task_to_dict(t) for t in sorted_tasks]

    async def work_breakdown(
        self, goal: str, project_id: str, priority: str = "medium"
    ) -> dict:
        plan = await self.create_plan(project_id, goal, priority)

        phases = await self._generate_phases(goal)
        for phase_data in phases:
            parent = await self.add_plan_task(
                plan_id=plan.plan_id,
                title=phase_data["title"],
                description=phase_data.get("description"),
                priority=priority,
                sort_order=phase_data.get("sort_order", 0),
            )
            for subtask in phase_data.get("tasks", []):
                await self.add_plan_task(
                    plan_id=plan.plan_id,
                    title=subtask["title"],
                    description=subtask.get("description"),
                    priority=subtask.get("priority", "medium"),
                    estimated_hours=subtask.get("estimated_hours"),
                    parent_task_id=parent.task_id,
                    sort_order=subtask.get("sort_order", 0),
                )

        return {
            "plan_id": plan.plan_id,
            "goal": goal,
            "phases": phases,
        }

    async def _generate_phases(self, goal: str) -> list[dict]:
        return [
            {
                "title": "Requirements & Analysis",
                "description": f"Analyze requirements for: {goal}",
                "sort_order": 0,
                "tasks": [
                    {"title": "Gather requirements", "sort_order": 0, "estimated_hours": 4},
                    {"title": "Define acceptance criteria", "sort_order": 1, "estimated_hours": 2},
                ],
            },
            {
                "title": "Design",
                "description": f"Design solution for: {goal}",
                "sort_order": 1,
                "tasks": [
                    {"title": "Architecture design", "sort_order": 0, "estimated_hours": 6},
                    {"title": "Interface specification", "sort_order": 1, "estimated_hours": 3},
                ],
            },
            {
                "title": "Implementation",
                "description": f"Implement: {goal}",
                "sort_order": 2,
                "tasks": [
                    {"title": "Core implementation", "sort_order": 0, "estimated_hours": 16},
                    {"title": "Unit tests", "sort_order": 1, "estimated_hours": 4},
                ],
            },
            {
                "title": "Testing & Review",
                "description": f"Test and review: {goal}",
                "sort_order": 3,
                "tasks": [
                    {"title": "Integration testing", "sort_order": 0, "estimated_hours": 6},
                    {"title": "Code review", "sort_order": 1, "estimated_hours": 2},
                ],
            },
            {
                "title": "Deployment",
                "description": f"Deploy: {goal}",
                "sort_order": 4,
                "tasks": [
                    {"title": "Release preparation", "sort_order": 0, "estimated_hours": 2},
                    {"title": "Deploy to production", "sort_order": 1, "estimated_hours": 1},
                ],
            },
        ]

    def _plan_to_dict(self, p: ProjectPlan) -> dict:
        return {
            "plan_id": p.plan_id,
            "project_id": p.project_id,
            "goal": p.goal,
            "status": p.status,
            "priority": p.priority,
            "overall_risk_score": p.overall_risk_score,
            "notes": p.notes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }

    def _task_to_dict(self, t: PlanTask) -> dict:
        return {
            "task_id": t.task_id,
            "plan_id": t.plan_id,
            "parent_task_id": t.parent_task_id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "risk_score": t.risk_score,
            "risk_factors": json.loads(t.risk_factors) if t.risk_factors else None,
            "estimated_hours": t.estimated_hours,
            "dependencies": json.loads(t.dependencies) if t.dependencies else [],
            "assigned_agent_type": t.assigned_agent_type,
            "sort_order": t.sort_order,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }

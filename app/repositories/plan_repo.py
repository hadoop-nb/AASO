from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import PlanTask, ProjectPlan
from app.repositories.base import BaseRepository


class ProjectPlanRepository(BaseRepository[ProjectPlan]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ProjectPlan)

    async def list_by_project(
        self, project_id: str, limit: int = 20, offset: int = 0
    ) -> list[ProjectPlan]:
        stmt = (
            select(ProjectPlan)
            .where(ProjectPlan.project_id == project_id)
            .order_by(ProjectPlan.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PlanTaskRepository(BaseRepository[PlanTask]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PlanTask)

    async def list_by_plan(
        self, plan_id: str, limit: int = 200, offset: int = 0
    ) -> list[PlanTask]:
        stmt = (
            select(PlanTask)
            .where(PlanTask.plan_id == plan_id)
            .order_by(PlanTask.sort_order, PlanTask.created_at)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_parent(
        self, parent_task_id: str
    ) -> list[PlanTask]:
        stmt = (
            select(PlanTask)
            .where(PlanTask.parent_task_id == parent_task_id)
            .order_by(PlanTask.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

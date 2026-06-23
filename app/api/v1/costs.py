from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.cost_tracker import CostTracker, cost_tracker as default_tracker

router = APIRouter(prefix="/projects/{project_id}/costs")


@router.get("")
async def get_project_costs(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    tracker: CostTracker = Depends(lambda: default_tracker),
):
    tracker.set_session(session)
    return await tracker.get_project_summary(project_id)


@router.get("/details")
async def get_project_cost_details(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    tracker: CostTracker = Depends(lambda: default_tracker),
):
    from app.repositories.cost_repo import CostRepository

    repo = CostRepository(session)
    entries = await repo.list_by_project(project_id)
    return [
        {
            "cost_id": e.cost_id,
            "model": e.model,
            "provider": e.provider,
            "prompt_tokens": e.prompt_tokens,
            "completion_tokens": e.completion_tokens,
            "total_tokens": e.total_tokens,
            "cost_usd": e.cost_usd,
            "agent_type": e.agent_type,
            "executed_at": e.executed_at.isoformat(),
        }
        for e in entries
    ]


overview_router = APIRouter(prefix="/costs")


@overview_router.get("/overall")
async def get_overall_costs(
    session: AsyncSession = Depends(get_db),
    tracker: CostTracker = Depends(lambda: default_tracker),
):
    tracker.set_session(session)
    return await tracker.get_overall_stats()


@overview_router.get("/by-model")
async def get_costs_by_model(
    session: AsyncSession = Depends(get_db),
    tracker: CostTracker = Depends(lambda: default_tracker),
):
    tracker.set_session(session)
    return await tracker.get_cost_by_model()

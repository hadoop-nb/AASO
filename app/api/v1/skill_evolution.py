from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.skill_evolution_service import SkillEvolutionService

router = APIRouter(prefix="/skills")


@router.post("/assessments")
async def record_assessment(
    agent_type: str,
    agent_id: str,
    score: float = Query(..., ge=0, le=10),
    confidence: float = Query(1.0, ge=0, le=1),
    run_id: str | None = None,
    task_id: str | None = None,
    project_id: str | None = None,
    strengths: str | None = None,
    weaknesses: str | None = None,
    notes: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    svc = SkillEvolutionService(session)
    assessment = await svc.record_assessment(
        agent_type, agent_id, score, confidence,
        run_id, task_id, project_id, strengths, weaknesses, notes,
    )
    return {"assessment_id": assessment.assessment_id, "score": assessment.score}


@router.get("/assessments")
async def list_assessments(
    agent_type: str | None = None,
    project_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    svc = SkillEvolutionService(session)
    return await svc.get_assessment_history(agent_type, project_id, limit, offset)


@router.get("/performance")
async def agent_performance(
    agent_type: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    svc = SkillEvolutionService(session)
    return await svc.get_agent_performance(agent_type)


@router.post("/prompts")
async def create_prompt_template(
    agent_type: str,
    name: str,
    system_prompt: str,
    user_prompt_template: str | None = None,
    change_notes: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    svc = SkillEvolutionService(session)
    template = await svc.create_prompt_template(
        agent_type, name, system_prompt, user_prompt_template, change_notes,
    )
    return {
        "template_id": template.template_id,
        "agent_type": template.agent_type,
        "version": template.version,
    }


@router.get("/prompts")
async def list_prompts(
    agent_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    svc = SkillEvolutionService(session)
    return await svc.list_prompt_templates(agent_type, limit, offset)


@router.get("/prompts/active")
async def get_active_prompt(
    agent_type: str,
    session: AsyncSession = Depends(get_db),
):
    svc = SkillEvolutionService(session)
    prompt = await svc.get_active_prompt(agent_type)
    if not prompt:
        return {"error": "No active prompt for agent type", "agent_type": agent_type}
    return prompt


@router.get("/ab-test")
async def compare_ab_test(
    agent_type: str,
    version_a: int,
    version_b: int,
    session: AsyncSession = Depends(get_db),
):
    svc = SkillEvolutionService(session)
    return await svc.compare_ab_test(agent_type, version_a, version_b)

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    code_files,
    collaboration,
    costs,
    decisions,
    developer,
    events,
    experience,
    knowledge_graph,
    lessons,
    memory,
    meta_agent,
    orchestrator,
    pipelines,
    projects,
    qa,
    research,
    review,
    tasks,
    workforce,
    workflows,
)

router = APIRouter(prefix="/api/v1")

router.include_router(projects.router, tags=["projects"])
router.include_router(tasks.router, tags=["tasks"])
router.include_router(decisions.router, tags=["decisions"])
router.include_router(lessons.router, tags=["lessons"])
router.include_router(memory.router, tags=["memory"])
router.include_router(code_files.router, tags=["code"])
router.include_router(developer.router, tags=["agents"])
router.include_router(workflows.router, tags=["workflows"])
router.include_router(qa.router, tags=["qa"])
router.include_router(review.router, tags=["review"])
router.include_router(analytics.router, tags=["analytics"])
router.include_router(experience.router, tags=["experience"])
router.include_router(orchestrator.router, tags=["orchestrator"])
router.include_router(pipelines.router, tags=["pipelines"])
router.include_router(research.router, tags=["research"])
router.include_router(costs.router, tags=["costs"])
router.include_router(costs.overview_router, tags=["costs"])
router.include_router(events.router, tags=["events"])
router.include_router(workforce.router, tags=["workforce"])
router.include_router(collaboration.router, tags=["collaboration"])
router.include_router(knowledge_graph.router, tags=["knowledge-graph"])
router.include_router(meta_agent.router, tags=["meta-agent"])

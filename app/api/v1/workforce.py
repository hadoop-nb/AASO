from fastapi import APIRouter, Depends, Query

from app.services.workforce_service import WorkforceService, workforce_service as default_ws

router = APIRouter(prefix="/workforce")


@router.get("/agents")
async def list_agents(
    agent_type: str | None = Query(None),
    status: str | None = Query(None),
    ws: WorkforceService = Depends(lambda: default_ws),
):
    from app.core.agent_pool import AgentStatus

    status_enum = None
    if status:
        try:
            status_enum = AgentStatus(status)
        except ValueError:
            pass
    return ws.list_agents(agent_type=agent_type, status=status_enum)


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    ws: WorkforceService = Depends(lambda: default_ws),
):
    agent = ws.get_agent(agent_id)
    if not agent:
        return {"error": "Agent not found", "agent_id": agent_id}
    return {
        "agent_id": agent.agent_id,
        "agent_type": agent.agent_type,
        "status": agent.status.value,
        "current_task_id": agent.current_task_id,
        "current_project_id": agent.current_project_id,
        "completed_tasks": agent.completed_tasks,
        "error_count": agent.error_count,
        "is_available": agent.is_available,
    }


@router.post("/agents/{agent_type}/register")
async def register_agent(
    agent_type: str,
    ws: WorkforceService = Depends(lambda: default_ws),
):
    agent = ws.register_agent(agent_type)
    return {
        "agent_id": agent.agent_id,
        "agent_type": agent.agent_type,
        "status": agent.status.value,
    }


@router.post("/agents/{agent_id}/unregister")
async def unregister_agent(
    agent_id: str,
    ws: WorkforceService = Depends(lambda: default_ws),
):
    success = ws.unregister_agent(agent_id)
    return {"success": success, "agent_id": agent_id}


@router.get("/summary")
async def pool_summary(
    ws: WorkforceService = Depends(lambda: default_ws),
):
    return ws.get_pool_summary()


@router.post("/auto-register")
async def auto_register(
    ws: WorkforceService = Depends(lambda: default_ws),
):
    ws.auto_register_standard_agents()
    return ws.get_pool_summary()

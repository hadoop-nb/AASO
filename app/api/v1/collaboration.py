from fastapi import APIRouter, Depends, Query

from app.core.agent_protocol import (
    message_router,
    shared_workspace,
)

router = APIRouter(prefix="/projects/{project_id}/collaboration")


@router.get("/threads")
async def list_threads(
    project_id: str,
    protocol: str | None = Query(None),
    status: str | None = Query(None),
):
    threads = message_router.list_threads(protocol=protocol, status=status)
    return [
        {
            "thread_id": t.thread_id,
            "protocol": t.protocol,
            "participants": t.participants,
            "message_count": len(t.messages),
            "status": t.status,
            "started_at": t.started_at.isoformat(),
            "context": t.context,
        }
        for t in threads
    ]


@router.get("/threads/{thread_id}")
async def get_thread(project_id: str, thread_id: str):
    thread = message_router.get_thread(thread_id)
    if not thread:
        return {"error": "Thread not found", "thread_id": thread_id}
    return {
        "thread_id": thread.thread_id,
        "protocol": thread.protocol,
        "participants": thread.participants,
        "messages": [
            {
                "message_id": m.message_id,
                "protocol": m.protocol,
                "payload": m.payload,
                "source_agent": m.source_agent,
                "target_agent": m.target_agent,
                "status": m.status.value,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in thread.messages
        ],
        "status": thread.status,
        "started_at": thread.started_at.isoformat(),
        "context": thread.context,
    }


@router.post("/threads/{thread_id}/close")
async def close_thread(project_id: str, thread_id: str):
    success = message_router.close_thread(thread_id)
    return {"success": success, "thread_id": thread_id}


@router.get("/workspace")
async def list_workspace(project_id: str):
    return shared_workspace.to_dict()


@router.get("/workspace/{key}")
async def get_workspace_key(project_id: str, key: str):
    value = shared_workspace.get(key)
    if value is None:
        return {"error": "Key not found", "key": key}
    return value


@router.put("/workspace/{key}")
async def set_workspace_key(
    project_id: str,
    key: str,
    body: dict,
):
    shared_workspace.set(key, body.get("value", {}), created_by=body.get("created_by", "api"))
    return {"success": True, "key": key}


@router.delete("/workspace/{key}")
async def delete_workspace_key(project_id: str, key: str):
    success = shared_workspace.delete(key)
    return {"success": success, "key": key}

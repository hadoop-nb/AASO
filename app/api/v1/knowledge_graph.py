from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.knowledge_graph_service import KnowledgeGraphService

router = APIRouter(prefix="/knowledge")


@router.post("/nodes")
async def create_node(
    project_id: str | None = None,
    node_type: str = "concept",
    title: str = "",
    content: str | None = None,
    metadata: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    import json
    svc = KnowledgeGraphService(session)
    parsed = json.loads(metadata) if metadata else None
    node = await svc.create_node(project_id, node_type, title, content, parsed)
    return {
        "node_id": node.node_id,
        "node_type": node.node_type,
        "title": node.title,
    }


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = KnowledgeGraphService(session)
    node = await svc.get_node(node_id)
    if not node:
        return {"error": "Node not found", "node_id": node_id}
    return {
        "node_id": node.node_id,
        "project_id": node.project_id,
        "node_type": node.node_type,
        "title": node.title,
        "content": node.content,
        "metadata": node.metadata_json,
        "created_at": node.created_at.isoformat() if node.created_at else None,
    }


@router.delete("/nodes/{node_id}")
async def delete_node(
    node_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = KnowledgeGraphService(session)
    success = await svc.delete_node(node_id)
    return {"success": success, "node_id": node_id}


@router.get("/nodes/{node_id}/edges")
async def get_node_edges(
    node_id: str,
    direction: str = Query("both", pattern="^(both|incoming|outgoing)$"),
    session: AsyncSession = Depends(get_db),
):
    svc = KnowledgeGraphService(session)
    return await svc.get_node_edges(node_id, direction)


@router.get("/nodes/{node_id}/impact")
async def impact_analysis(
    node_id: str,
    max_depth: int = Query(3, ge=1, le=10),
    session: AsyncSession = Depends(get_db),
):
    svc = KnowledgeGraphService(session)
    return await svc.get_impact_analysis(node_id, max_depth)


@router.get("/nodes/{node_id}/root-cause")
async def root_cause_analysis(
    node_id: str,
    max_depth: int = Query(3, ge=1, le=10),
    session: AsyncSession = Depends(get_db),
):
    svc = KnowledgeGraphService(session)
    return await svc.get_root_cause_analysis(node_id, max_depth)


@router.post("/edges")
async def create_edge(
    source_node_id: str,
    target_node_id: str,
    relationship_type: str,
    weight: float = 1.0,
    metadata: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    import json
    svc = KnowledgeGraphService(session)
    parsed = json.loads(metadata) if metadata else None
    edge = await svc.create_edge(source_node_id, target_node_id, relationship_type, weight, parsed)
    return {
        "edge_id": edge.edge_id,
        "source_node_id": edge.source_node_id,
        "target_node_id": edge.target_node_id,
        "relationship_type": edge.relationship_type,
    }


@router.get("/paths")
async def find_paths(
    source_id: str,
    target_id: str,
    max_depth: int = Query(5, ge=1, le=10),
    session: AsyncSession = Depends(get_db),
):
    svc = KnowledgeGraphService(session)
    return await svc.find_paths(source_id, target_id, max_depth)


@router.get("/projects/{project_id}/graph")
async def project_graph(
    project_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = KnowledgeGraphService(session)
    return await svc.get_project_graph(project_id)


@router.post("/projects/{project_id}/auto-index")
async def auto_index_project(
    project_id: str,
    session: AsyncSession = Depends(get_db),
):
    svc = KnowledgeGraphService(session)
    count = await svc.auto_index_project(project_id, session)
    return {"project_id": project_id, "nodes_created": count}

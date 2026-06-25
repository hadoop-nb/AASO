from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_node import KnowledgeNode, KnowledgeEdge
from app.repositories.knowledge_repo import (
    KnowledgeNodeRepository,
    KnowledgeEdgeRepository,
)

logger = logging.getLogger(__name__)

NODE_TYPES = {"decision", "lesson", "task", "code_file", "project", "agent_run", "concept"}
RELATIONSHIP_TYPES = {
    "leads_to", "depends_on", "addresses", "generates",
    "related_to", "part_of", "blocked_by", "resolves",
}


class KnowledgeGraphService:
    def __init__(self, session: AsyncSession):
        self._node_repo = KnowledgeNodeRepository(session)
        self._edge_repo = KnowledgeEdgeRepository(session)
        self._session = session

    async def create_node(
        self,
        project_id: str | None,
        node_type: str,
        title: str,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> KnowledgeNode:
        if node_type not in NODE_TYPES:
            raise ValueError(f"Invalid node_type '{node_type}'. Must be one of: {NODE_TYPES}")
        data = {
            "project_id": project_id,
            "node_type": node_type,
            "title": title,
            "content": content,
            "metadata_json": json.dumps(metadata) if metadata else None,
        }
        return await self._node_repo.create(data)

    async def create_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        relationship_type: str,
        weight: float = 1.0,
        metadata: dict | None = None,
    ) -> KnowledgeEdge:
        if relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(
                f"Invalid relationship_type '{relationship_type}'. "
                f"Must be one of: {RELATIONSHIP_TYPES}"
            )

        source = await self._node_repo.get(source_node_id)
        if not source:
            raise ValueError(f"Source node {source_node_id} not found")
        target = await self._node_repo.get(target_node_id)
        if not target:
            raise ValueError(f"Target node {target_node_id} not found")

        data = {
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "relationship_type": relationship_type,
            "weight": weight,
            "metadata_json": json.dumps(metadata) if metadata else None,
        }
        return await self._edge_repo.create(data)

    async def get_node(self, node_id: str) -> KnowledgeNode | None:
        return await self._node_repo.get(node_id)

    async def delete_node(self, node_id: str) -> bool:
        node = await self._node_repo.get(node_id)
        if not node:
            return False

        edges = await self._edge_repo.get_outgoing(node_id)
        for e in edges:
            await self._edge_repo.delete(e.edge_id)
        edges = await self._edge_repo.get_incoming(node_id)
        for e in edges:
            await self._edge_repo.delete(e.edge_id)

        return await self._node_repo.delete(node_id)

    async def list_project_nodes(
        self, project_id: str, node_type: str | None = None
    ) -> list[dict]:
        nodes = await self._node_repo.list_by_project(project_id, node_type)
        return [self._node_to_dict(n) for n in nodes]

    async def get_node_edges(
        self, node_id: str, direction: str = "both"
    ) -> dict:
        outgoing = await self._edge_repo.get_outgoing(node_id) if direction in ("outgoing", "both") else []
        incoming = await self._edge_repo.get_incoming(node_id) if direction in ("incoming", "both") else []
        return {
            "node_id": node_id,
            "outgoing": [self._edge_to_dict(e) for e in outgoing],
            "incoming": [self._edge_to_dict(e) for e in incoming],
        }

    async def find_paths(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> list[list[dict]]:
        return await self._edge_repo.find_paths(source_id, target_id, max_depth)

    async def get_impact_analysis(
        self, node_id: str, max_depth: int = 3
    ) -> list[dict]:
        return await self._edge_repo.get_downstream_nodes(node_id, max_depth)

    async def get_root_cause_analysis(
        self, node_id: str, max_depth: int = 3
    ) -> list[dict]:
        return await self._edge_repo.get_upstream_nodes(node_id, max_depth)

    async def get_project_graph(
        self, project_id: str
    ) -> dict:
        nodes = await self._node_repo.list_by_project(project_id)
        node_ids = {n.node_id for n in nodes}
        edges = []
        for e in await self._edge_repo.get_all_edges_for_project(project_id):
            if e.source_node_id in node_ids and e.target_node_id in node_ids:
                edges.append(self._edge_to_dict(e))
        return {
            "project_id": project_id,
            "nodes": [self._node_to_dict(n) for n in nodes],
            "edges": edges,
        }

    async def auto_index_project(self, project_id: str, session: AsyncSession) -> int:
        """Auto-create nodes from existing project entities (tasks, decisions, lessons)."""
        from sqlalchemy import select, func
        from app.models.task import Task
        from app.models.decision import Decision
        from app.models.lesson import Lesson

        count = 0

        result = await session.execute(
            select(Task).where(Task.project_id == project_id)
        )
        for task in result.scalars().all():
            await self.create_node(
                project_id=project_id,
                node_type="task",
                title=task.title or f"Task {task.task_id}",
                content=task.description,
            )
            count += 1

        result = await session.execute(
            select(Decision).where(Decision.project_id == project_id)
        )
        for dec in result.scalars().all():
            await self.create_node(
                project_id=project_id,
                node_type="decision",
                title=dec.question,
                content=dec.selected,
            )
            count += 1

        result = await session.execute(
            select(Lesson).where(Lesson.project_id == project_id)
        )
        for lesson in result.scalars().all():
            await self.create_node(
                project_id=project_id,
                node_type="lesson",
                title=lesson.problem,
                content=lesson.solution,
            )
            count += 1

        return count

    def _node_to_dict(self, node: KnowledgeNode) -> dict:
        return {
            "node_id": node.node_id,
            "project_id": node.project_id,
            "node_type": node.node_type,
            "title": node.title,
            "content": node.content,
            "metadata": json.loads(node.metadata_json) if node.metadata_json else None,
            "created_at": node.created_at.isoformat() if node.created_at else None,
        }

    def _edge_to_dict(self, edge: KnowledgeEdge) -> dict:
        return {
            "edge_id": edge.edge_id,
            "source_node_id": edge.source_node_id,
            "target_node_id": edge.target_node_id,
            "relationship_type": edge.relationship_type,
            "weight": edge.weight,
            "metadata": json.loads(edge.metadata_json) if edge.metadata_json else None,
            "created_at": edge.created_at.isoformat() if edge.created_at else None,
        }

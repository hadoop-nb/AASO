from collections import deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_node import KnowledgeNode, KnowledgeEdge
from app.repositories.base import BaseRepository


class KnowledgeNodeRepository(BaseRepository[KnowledgeNode]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, KnowledgeNode)

    async def list_by_project(
        self, project_id: str, node_type: str | None = None
    ) -> list[KnowledgeNode]:
        stmt = select(KnowledgeNode).where(
            KnowledgeNode.project_id == project_id
        )
        if node_type:
            stmt = stmt.where(KnowledgeNode.node_type == node_type)
        stmt = stmt.order_by(KnowledgeNode.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class KnowledgeEdgeRepository(BaseRepository[KnowledgeEdge]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, KnowledgeEdge)

    async def get_outgoing(self, node_id: str) -> list[KnowledgeEdge]:
        stmt = (
            select(KnowledgeEdge)
            .where(KnowledgeEdge.source_node_id == node_id)
            .order_by(KnowledgeEdge.weight.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_incoming(self, node_id: str) -> list[KnowledgeEdge]:
        stmt = (
            select(KnowledgeEdge)
            .where(KnowledgeEdge.target_node_id == node_id)
            .order_by(KnowledgeEdge.weight.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_edges_for_project(
        self, project_id: str
    ) -> list[KnowledgeEdge]:
        """Get all edges where both source and target belong to a project."""
        from sqlalchemy import exists

        node_subq = (
            select(KnowledgeNode.node_id)
            .where(KnowledgeNode.project_id == project_id)
            .subquery()
        )
        stmt = select(KnowledgeEdge).where(
            KnowledgeEdge.source_node_id.in_(select(node_subq.c.node_id)),
            KnowledgeEdge.target_node_id.in_(select(node_subq.c.node_id)),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _build_adjacency(
        self, node_ids: set[str]
    ) -> tuple[dict[str, list[tuple[str, str, float]]], dict[str, list[tuple[str, str, float]]]]:
        """Build forward and reverse adjacency lists for a set of node IDs."""
        outgoing: dict[str, list[tuple[str, str, float]]] = {n: [] for n in node_ids}
        incoming: dict[str, list[tuple[str, str, float]]] = {n: [] for n in node_ids}

        stmt = select(KnowledgeEdge).where(
            KnowledgeEdge.source_node_id.in_(list(node_ids)),
            KnowledgeEdge.target_node_id.in_(list(node_ids)),
        )
        result = await self.session.execute(stmt)
        edges = list(result.scalars().all())

        for e in edges:
            if e.source_node_id in outgoing:
                outgoing[e.source_node_id].append(
                    (e.target_node_id, e.relationship_type, e.weight)
                )
            if e.target_node_id in incoming:
                incoming[e.target_node_id].append(
                    (e.source_node_id, e.relationship_type, e.weight)
                )

        return outgoing, incoming

    async def find_paths(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> list[list[dict]]:
        """BFS-based path finding between two nodes."""
        if max_depth < 1:
            return []

        visited: set[str] = set()
        queue: deque[tuple[str, int, list[dict]]] = deque()
        queue.append((source_id, 0, []))
        visited.add(source_id)

        results: list[list[dict]] = []

        while queue:
            current, depth, path = queue.popleft()

            if current == target_id and path:
                results.append(path)
                continue

            if depth >= max_depth:
                continue

            edges = await self.get_outgoing(current)
            for edge in edges:
                nid = edge.target_node_id
                new_path = path + [
                    {
                        "source": current,
                        "target": nid,
                        "relationship": edge.relationship_type,
                        "weight": edge.weight,
                        "depth": depth + 1,
                    }
                ]
                if nid == target_id:
                    results.append(new_path)
                elif nid not in visited:
                    visited.add(nid)
                    queue.append((nid, depth + 1, new_path))

        return results

    async def get_downstream_nodes(
        self, node_id: str, max_depth: int = 3
    ) -> list[dict]:
        """BFS downstream traversal for impact analysis."""
        visited: set[str] = set()
        queue: deque[tuple[str, int, list[str]]] = deque()
        queue.append((node_id, 0, []))
        results: list[dict] = []

        while queue:
            current, depth, path = queue.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            edges = await self.get_outgoing(current)
            for edge in edges:
                if edge.target_node_id not in visited:
                    new_path = path + [edge.target_node_id]
                    results.append({
                        "node_id": edge.target_node_id,
                        "source_node_id": current,
                        "relationship": edge.relationship_type,
                        "weight": edge.weight,
                        "depth": depth + 1,
                        "path": new_path,
                    })
                    queue.append(
                        (edge.target_node_id, depth + 1, new_path)
                    )

        return results

    async def get_upstream_nodes(
        self, node_id: str, max_depth: int = 3
    ) -> list[dict]:
        """BFS upstream traversal for root cause analysis."""
        visited: set[str] = set()
        queue: deque[tuple[str, int, list[str]]] = deque()
        queue.append((node_id, 0, []))
        results: list[dict] = []

        while queue:
            current, depth, path = queue.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            edges = await self.get_incoming(current)
            for edge in edges:
                if edge.source_node_id not in visited:
                    new_path = path + [edge.source_node_id]
                    results.append({
                        "node_id": edge.source_node_id,
                        "target_node_id": current,
                        "relationship": edge.relationship_type,
                        "weight": edge.weight,
                        "depth": depth + 1,
                        "path": new_path,
                    })
                    queue.append(
                        (edge.source_node_id, depth + 1, new_path)
                    )

        return results

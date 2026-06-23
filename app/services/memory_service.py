from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient, models

from app.config import settings
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, qdrant: AsyncQdrantClient):
        self.qdrant = qdrant

    async def ensure_collection(self):
        try:
            collections = await self.qdrant.get_collections()
            names = [c.name for c in collections.collections]
            if settings.qdrant_collection not in names:
                await self.qdrant.create_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config=models.VectorParams(
                        size=settings.embedding_dimension,
                        distance=models.Distance.COSINE,
                    ),
                )
        except Exception as exc:
            logger.warning("Qdrant unavailable: %s", exc)

    async def index_entity(
        self,
        entity_type: str,
        entity_id: str,
        project_id: str,
        content: str,
    ) -> bool:
        try:
            embedding = await embedding_service.embed_async(content)
            point_id = f"{entity_type}_{entity_id}"
            await self.qdrant.upsert(
                collection_name=settings.qdrant_collection,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "project_id": project_id,
                            "content": content,
                        },
                    )
                ],
            )
            return True
        except Exception as exc:
            logger.warning("Qdrant index_entity failed: %s", exc)
            return False

    async def query(
        self,
        project_id: str,
        query: str,
        filter_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        try:
            embedding = await embedding_service.embed_async(query)
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="project_id",
                        match=models.MatchValue(value=project_id),
                    )
                ]
            )
            if filter_types:
                query_filter.must.append(
                    models.FieldCondition(
                        key="entity_type",
                        match=models.MatchAny(any=filter_types),
                    )
                )
            result = await self.qdrant.query_points(
                collection_name=settings.qdrant_collection,
                query=embedding,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "entity_type": p.payload.get("entity_type"),
                    "entity_id": p.payload.get("entity_id"),
                    "content": p.payload.get("content"),
                    "score": p.score,
                }
                for p in result.points
            ]
        except Exception as exc:
            logger.warning("Qdrant query failed: %s", exc)
            return []

    async def delete_entity(
        self, entity_type: str, entity_id: str
    ) -> bool:
        try:
            point_id = f"{entity_type}_{entity_id}"
            await self.qdrant.delete(
                collection_name=settings.qdrant_collection,
                points_selector=models.PointIdsList(
                    points=[point_id]
                ),
            )
            return True
        except Exception as exc:
            logger.warning("Qdrant delete_entity failed: %s", exc)
            return False

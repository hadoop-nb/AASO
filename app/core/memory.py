from qdrant_client import AsyncQdrantClient

from app.config import settings

qdrant_client = AsyncQdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
    prefer_grpc=False,
)


async def get_qdrant() -> AsyncQdrantClient:
    return qdrant_client

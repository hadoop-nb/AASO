from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router
from app.config import settings
from app.core.memory import qdrant_client
from app.services.memory_service import MemoryService


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = MemoryService(qdrant_client)
    await service.ensure_collection()
    yield
    await qdrant_client.close()


app = FastAPI(
    title="AASO - Adaptive AI Software Organization",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}

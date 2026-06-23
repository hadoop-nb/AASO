from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    def __init__(self):
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    @lru_cache(maxsize=1024)
    def embed(self, text: str) -> list[float]:
        model = self._get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    async def embed_async(self, text: str) -> list[float]:
        return self.embed(text)


embedding_service = EmbeddingService()

"""Embedding service wrapping sentence-transformers for local dev, swappable to OpenAI."""

import asyncio
from typing import Literal

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Embedding service with a local sentence-transformers backend.

    Uses all-MiniLM-L6-v2 (384-dim) for dev. Set backend="openai" and provide
    an api_key to use OpenAI ada-002 (1536-dim) in production.
    """

    def __init__(
        self,
        backend: Literal["local", "openai"] = "local",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        api_key: str | None = None,
    ):
        self.backend = backend
        self.model_name = model_name
        self._model = None
        self._api_key = api_key

        if backend == "local":
            self._model = SentenceTransformer(model_name)
            self.dimension = self._model.get_sentence_embedding_dimension()
        elif backend == "openai":
            self.dimension = 1536
        else:
            raise ValueError(f"Unknown backend: {backend}")

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        if self.backend == "local":
            # Run in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, lambda: self._model.encode(text, normalize_embeddings=True)
            )
            return embedding.tolist()
        elif self.backend == "openai":
            return await self._embed_openai([text])[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        if not texts:
            return []

        if self.backend == "local":
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, lambda: self._model.encode(texts, normalize_embeddings=True)
            )
            return [e.tolist() for e in embeddings]
        elif self.backend == "openai":
            return await self._embed_openai(texts)

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """Embed using OpenAI API."""
        import openai
        client = openai.AsyncOpenAI(api_key=self._api_key)
        response = await client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts,
        )
        return [item.embedding for item in response.data]

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.models import Chunk


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""
    chunk: Chunk
    score: float  # Similarity score


@dataclass
class VectorStoreConfig:
    """Configuration for vector store."""
    collection_name: str = "investor_memory"
    embedding_dimension: int = 1536  # OpenAI ada-002
    metric: str = "cosine"


class VectorStore:
    """
    Vector store for semantic search over chunks.

    Backends to consider:
    - Chroma (local, easy setup)
    - Pinecone (managed, scalable)
    - Qdrant (local or managed)
    - pgvector (if using Postgres anyway)
    """

    def __init__(self, config: VectorStoreConfig | None = None):
        self.config = config or VectorStoreConfig()
        # TODO: Initialize vector store client

    async def upsert(self, chunk: Chunk) -> None:
        """Insert or update a chunk with its embedding."""
        if chunk.embedding is None:
            raise ValueError("Chunk must have embedding before upserting")
        # TODO: Implement
        raise NotImplementedError

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filter_entity_ids: Optional[list[UUID]] = None,
    ) -> list[VectorSearchResult]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query vector
            limit: Max results to return
            filter_entity_ids: Only return chunks linked to these entities
        """
        # TODO: Implement
        raise NotImplementedError

    async def delete(self, chunk_id: UUID) -> None:
        """Delete a chunk from the store."""
        # TODO: Implement
        raise NotImplementedError

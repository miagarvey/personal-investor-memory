from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import chromadb

from src.models import Chunk, SourceType


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""
    chunk: Chunk
    score: float  # Similarity score


@dataclass
class VectorStoreConfig:
    """Configuration for vector store."""
    collection_name: str = "investor_memory"
    embedding_dimension: int = 384  # all-MiniLM-L6-v2
    metric: str = "cosine"
    persist_directory: str = "./chroma_data"


class VectorStore:
    """
    Vector store for semantic search over chunks using ChromaDB.
    """

    def __init__(self, config: VectorStoreConfig | None = None):
        self.config = config or VectorStoreConfig()
        self.client = chromadb.PersistentClient(path=self.config.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=self.config.collection_name,
            metadata={"hnsw:space": self.config.metric},
        )

    async def upsert(self, chunk: Chunk) -> None:
        """Insert or update a chunk with its embedding."""
        if chunk.embedding is None:
            raise ValueError("Chunk must have embedding before upserting")

        # Encode entity IDs as delimited string for filtering
        entity_ids_str = "|" + "|".join(str(eid) for eid in chunk.entity_ids) + "|" if chunk.entity_ids else ""

        metadata = {
            "source_id": str(chunk.source_id),
            "source_type": chunk.source_type.value,
            "entity_ids": entity_ids_str,
        }
        # Add any extra metadata (ChromaDB only supports str/int/float)
        for k, v in chunk.metadata.items():
            if isinstance(v, (str, int, float, bool)):
                metadata[f"meta_{k}"] = v

        self.collection.upsert(
            ids=[str(chunk.id)],
            embeddings=[chunk.embedding],
            documents=[chunk.text],
            metadatas=[metadata],
        )

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filter_entity_ids: Optional[list[UUID]] = None,
    ) -> list[VectorSearchResult]:
        """Search for similar chunks, optionally filtered by entity IDs."""
        # ChromaDB doesn't support substring filtering, so we'll fetch more results
        # and filter in Python if entity filters are provided
        fetch_limit = limit * 3 if filter_entity_ids else limit

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_limit,
        )

        search_results = []
        filter_set = {str(eid) for eid in filter_entity_ids} if filter_entity_ids else None

        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0.0
                doc = results["documents"][0][i] if results["documents"] else ""

                # Parse entity IDs back from delimited string
                entity_ids_str = meta.get("entity_ids", "")
                entity_ids = []
                if entity_ids_str:
                    parts = entity_ids_str.strip("|").split("|")
                    entity_ids = [UUID(p) for p in parts if p]

                # Apply entity filter in Python
                if filter_set:
                    chunk_entity_strs = {str(eid) for eid in entity_ids}
                    if not filter_set.intersection(chunk_entity_strs):
                        continue

                chunk = Chunk(
                    id=UUID(chunk_id),
                    text=doc,
                    source_id=UUID(meta.get("source_id", "00000000-0000-0000-0000-000000000000")),
                    source_type=SourceType(meta.get("source_type", "email")),
                    entity_ids=entity_ids,
                )

                # ChromaDB returns distances; convert to similarity
                score = 1.0 - distance if self.config.metric == "cosine" else -distance
                search_results.append(VectorSearchResult(chunk=chunk, score=score))

                if len(search_results) >= limit:
                    break

        return search_results

    async def delete(self, chunk_id: UUID) -> None:
        """Delete a chunk from the store."""
        self.collection.delete(ids=[str(chunk_id)])

    def reset(self):
        """Delete the collection and recreate it (for testing)."""
        self.client.delete_collection(self.config.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.config.collection_name,
            metadata={"hnsw:space": self.config.metric},
        )

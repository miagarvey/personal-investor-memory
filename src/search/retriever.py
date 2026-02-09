from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.models import Chunk, Company, Person
from src.storage.base import StorageBackend
from src.storage.vector import VectorStore, VectorSearchResult


@dataclass
class SearchResult:
    """Combined search result with context."""
    chunk: Chunk
    score: float
    company: Optional[Company] = None
    people: list[Person] | None = None


class Retriever:
    """
    Main retrieval interface for Phase 1.

    Supports two retrieval paths:
    1. Entity-based: Find all content related to a company/person
    2. Semantic: Find content similar to a query
    """

    def __init__(
        self,
        storage: StorageBackend,
        vector_store: VectorStore,
        embedding_fn=None,  # Function to embed text
    ):
        self.storage = storage
        self.vector_store = vector_store
        self.embedding_fn = embedding_fn

    async def search_by_company(
        self,
        company_id: UUID,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Find all content related to a company."""
        chunks = await self.storage.get_chunks_by_entity(company_id, limit=limit)
        company = await self.storage.get_company(company_id)

        results = []
        for chunk in chunks:
            results.append(SearchResult(
                chunk=chunk,
                score=1.0,
                company=company,
            ))
        return results

    async def search_by_person(
        self,
        person_id: UUID,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Find all content involving a person."""
        chunks = await self.storage.get_chunks_by_entity(person_id, limit=limit)
        person = await self.storage.get_person(person_id)

        results = []
        for chunk in chunks:
            results.append(SearchResult(
                chunk=chunk,
                score=1.0,
                people=[person] if person else None,
            ))
        return results

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filter_company_id: Optional[UUID] = None,
        filter_person_id: Optional[UUID] = None,
    ) -> list[SearchResult]:
        """
        Semantic search over all content.

        Optionally filter by entity.
        """
        if self.embedding_fn is None:
            raise ValueError("No embedding function configured")

        # Embed query
        query_embedding = await self.embedding_fn(query)

        # Build entity filter
        filter_ids = []
        if filter_company_id:
            filter_ids.append(filter_company_id)
        if filter_person_id:
            filter_ids.append(filter_person_id)

        # Search vector store
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            limit=limit,
            filter_entity_ids=filter_ids if filter_ids else None,
        )

        # Enrich with context
        return [await self._enrich_result(r) for r in results]

    async def find_related(
        self,
        query: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Main search entry point: find past discussions related to query.

        This is the primary Phase 1 use case.
        """
        return await self.semantic_search(query=query, limit=limit)

    async def _enrich_result(self, result: VectorSearchResult) -> SearchResult:
        """Add entity context to a search result."""
        chunk = result.chunk

        company = None
        people = []

        for entity_id in chunk.entity_ids:
            c = await self.storage.get_company(entity_id)
            if c:
                company = c
                continue
            p = await self.storage.get_person(entity_id)
            if p:
                people.append(p)

        return SearchResult(
            chunk=chunk,
            score=result.score,
            company=company,
            people=people if people else None,
        )

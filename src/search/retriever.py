from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.models import Chunk, Company, Person, Theme
from src.storage.base import StorageBackend
from src.storage.vector import VectorStore, VectorSearchResult


@dataclass
class SearchResult:
    """Combined search result with context."""
    chunk: Chunk
    score: float
    company: Optional[Company] = None
    people: list[Person] | None = None
    themes: list[Theme] | None = None


class Retriever:
    """
    Main retrieval interface for Phase 1.

    Supports two retrieval paths:
    1. Entity-based: Find all content related to a company/person
    2. Semantic: Find content similar to a query

    Goal: "Here are all past conversations and docs related to
    this company / pattern"
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
        """
        Find all content related to a company.

        Uses entity-based retrieval from relational store.
        """
        # TODO: Implement
        # 1. Get all chunks linked to this company
        # 2. Get associated interactions/artifacts
        # 3. Return with context
        raise NotImplementedError

    async def search_by_person(
        self,
        person_id: UUID,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Find all content involving a person."""
        # TODO: Implement
        raise NotImplementedError

    async def search_by_theme(
        self,
        theme_id: UUID,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Find all content related to a theme."""
        # TODO: Implement
        raise NotImplementedError

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

        # Fetch linked entities
        company = None
        people = []
        themes = []

        for entity_id in chunk.entity_ids:
            # Try each entity type
            # TODO: Store entity type in chunk to avoid these lookups
            c = await self.storage.get_company(entity_id)
            if c:
                company = c
                continue
            p = await self.storage.get_person(entity_id)
            if p:
                people.append(p)
                continue
            t = await self.storage.get_theme(entity_id)
            if t:
                themes.append(t)

        return SearchResult(
            chunk=chunk,
            score=result.score,
            company=company,
            people=people if people else None,
            themes=themes if themes else None,
        )

"""Tests for the retriever."""

import pytest
from datetime import datetime

from src.models import SourceType
from src.search.retriever import Retriever


@pytest.mark.asyncio
async def test_search_by_company(pipeline, storage, vector_store, embedding_service):
    await pipeline.ingest_interaction(
        raw_text="NovaBuild has a platform. Strong growth trajectory.",
        source_type=SourceType.MEETING_NOTES,
        timestamp=datetime.utcnow(),
    )

    # Find NovaBuild in the DB
    companies = await storage.search_companies_by_name("NovaBuild")
    if not companies:
        pytest.skip("NovaBuild not extracted by spaCy in this context")

    retriever = Retriever(storage=storage, vector_store=vector_store, embedding_fn=embedding_service.embed)
    results = await retriever.search_by_company(companies[0].id)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_search_by_person(pipeline, storage, vector_store, embedding_service):
    await pipeline.ingest_interaction(
        raw_text="Sarah Chen presented the pitch deck to the team.",
        source_type=SourceType.MEETING_NOTES,
        timestamp=datetime.utcnow(),
    )

    people = await storage.search_people_by_name("Sarah Chen")
    if not people:
        pytest.skip("Sarah Chen not extracted by spaCy in this context")

    retriever = Retriever(storage=storage, vector_store=vector_store, embedding_fn=embedding_service.embed)
    results = await retriever.search_by_person(people[0].id)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_semantic_search(pipeline, storage, vector_store, embedding_service):
    await pipeline.ingest_interaction(
        raw_text="NovaBuild's tools have strong adoption among enterprise teams.",
        source_type=SourceType.MEETING_NOTES,
        timestamp=datetime.utcnow(),
    )

    retriever = Retriever(storage=storage, vector_store=vector_store, embedding_fn=embedding_service.embed)
    results = await retriever.semantic_search("enterprise tools")
    assert len(results) >= 1
    assert results[0].score > 0

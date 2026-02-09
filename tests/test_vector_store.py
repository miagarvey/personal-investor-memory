"""Tests for the ChromaDB vector store."""

import pytest
from uuid import uuid4

from src.models import Chunk, SourceType
from src.storage.vector import VectorStore


@pytest.mark.asyncio
async def test_upsert_and_search(vector_store, embedding_service):
    chunk = Chunk(
        text="NovaBuild is an enterprise SaaS company",
        source_id=uuid4(),
        source_type=SourceType.EMAIL,
        entity_ids=[uuid4()],
        embedding=await embedding_service.embed("NovaBuild is an enterprise SaaS company"),
    )
    await vector_store.upsert(chunk)

    query_emb = await embedding_service.embed("enterprise software")
    results = await vector_store.search(query_emb, limit=5)

    assert len(results) >= 1
    assert results[0].chunk.id == chunk.id
    assert results[0].score > 0


@pytest.mark.asyncio
async def test_upsert_requires_embedding(vector_store):
    chunk = Chunk(
        text="No embedding",
        source_id=uuid4(),
        source_type=SourceType.EMAIL,
    )
    with pytest.raises(ValueError, match="must have embedding"):
        await vector_store.upsert(chunk)


@pytest.mark.asyncio
async def test_search_with_entity_filter(vector_store, embedding_service):
    entity_a = uuid4()
    entity_b = uuid4()

    chunk_a = Chunk(
        text="Company A builds developer tools",
        source_id=uuid4(),
        source_type=SourceType.EMAIL,
        entity_ids=[entity_a],
        embedding=await embedding_service.embed("Company A builds developer tools"),
    )
    chunk_b = Chunk(
        text="Company B builds fintech products",
        source_id=uuid4(),
        source_type=SourceType.EMAIL,
        entity_ids=[entity_b],
        embedding=await embedding_service.embed("Company B builds fintech products"),
    )
    await vector_store.upsert(chunk_a)
    await vector_store.upsert(chunk_b)

    query_emb = await embedding_service.embed("software tools")
    results = await vector_store.search(query_emb, limit=5, filter_entity_ids=[entity_a])

    assert len(results) >= 1
    assert all(entity_a in r.chunk.entity_ids for r in results)


@pytest.mark.asyncio
async def test_delete(vector_store, embedding_service):
    chunk = Chunk(
        text="Delete me",
        source_id=uuid4(),
        source_type=SourceType.EMAIL,
        embedding=await embedding_service.embed("Delete me"),
    )
    await vector_store.upsert(chunk)
    await vector_store.delete(chunk.id)

    query_emb = await embedding_service.embed("Delete me")
    results = await vector_store.search(query_emb, limit=5)
    assert all(r.chunk.id != chunk.id for r in results)

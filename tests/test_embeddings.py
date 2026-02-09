"""Tests for the embedding service."""

import pytest


@pytest.mark.asyncio
async def test_embed_returns_correct_dimension(embedding_service):
    result = await embedding_service.embed("Hello world")
    assert isinstance(result, list)
    assert len(result) == 384  # all-MiniLM-L6-v2 dimension


@pytest.mark.asyncio
async def test_embed_batch(embedding_service):
    texts = ["Hello world", "Goodbye world", "Enterprise SaaS"]
    results = await embedding_service.embed_batch(texts)
    assert len(results) == 3
    for r in results:
        assert len(r) == 384


@pytest.mark.asyncio
async def test_embed_batch_empty(embedding_service):
    results = await embedding_service.embed_batch([])
    assert results == []


@pytest.mark.asyncio
async def test_similar_texts_have_high_similarity(embedding_service):
    import numpy as np
    e1 = await embedding_service.embed("enterprise software company")
    e2 = await embedding_service.embed("business SaaS platform")
    e3 = await embedding_service.embed("cute fluffy puppies")

    sim_related = np.dot(e1, e2)
    sim_unrelated = np.dot(e1, e3)
    assert sim_related > sim_unrelated

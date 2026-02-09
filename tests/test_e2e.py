"""End-to-end test: seed data → verify entity dedup → entity search → semantic search."""

import pytest
from datetime import datetime

from src.models import SourceType
from src.search.retriever import Retriever


@pytest.mark.asyncio
async def test_e2e_seed_and_search(pipeline, storage, vector_store, embedding_service):
    """Full end-to-end: ingest → entity dedup → entity search → semantic search."""

    # 1. Ingest content mentioning companies and people
    await pipeline.ingest_email(
        subject="Intro: NovaBuild - construction tech",
        body=(
            "NovaBuild is building an AI-powered construction management platform. "
            "Sarah Chen is the CEO. Strong growth with 80% gross margins."
        ),
        sender="Michael Torres",
        recipients=["team@fund.com"],
        timestamp=datetime.utcnow(),
    )

    await pipeline.ingest_meeting_notes(
        notes=(
            "Meeting with Sarah Chen of NovaBuild.\n\n"
            "## Product\n"
            "Platform for construction management. "
            "Strong product with good retention.\n\n"
            "## Concerns\n"
            "Market may be smaller than pitched.\n"
        ),
        meeting_title="NovaBuild First Meeting",
        attendees=["Michael Torres", "Sarah Chen"],
        timestamp=datetime.utcnow(),
    )

    await pipeline.ingest_email(
        subject="Intro: PayLoop - fintech",
        body=(
            "PayLoop is building real-time B2B payment orchestration. "
            "Marcus Rivera is the CEO/CTO. Strong competitive position."
        ),
        sender="Jessica Wu",
        recipients=["team@fund.com"],
        timestamp=datetime.utcnow(),
    )

    # 2. Verify entity deduplication
    # Sarah Chen should appear once (mentioned in two different documents)
    sarahs = await storage.search_people_by_name("Sarah Chen")
    assert len(sarahs) == 1, f"Expected 1 Sarah Chen, got {len(sarahs)}"

    # Michael Torres should appear once
    michaels = await storage.search_people_by_name("Michael Torres")
    assert len(michaels) == 1

    # 3. Entity-based search
    retriever = Retriever(
        storage=storage,
        vector_store=vector_store,
        embedding_fn=embedding_service.embed,
    )

    # Search by person (Sarah Chen)
    sarah = sarahs[0]
    person_results = await retriever.search_by_person(sarah.id)
    assert len(person_results) >= 1, "Should find chunks mentioning Sarah Chen"

    # 4. Semantic search
    sem_results = await retriever.semantic_search("construction platform management")
    assert len(sem_results) >= 1, "Semantic search should return results"
    # NovaBuild content should rank high for this query
    top_texts = [r.chunk.text for r in sem_results[:3]]
    assert any("NovaBuild" in t or "construction" in t for t in top_texts), \
        f"Expected NovaBuild-related content in top results, got: {top_texts}"

    # Fintech search should find PayLoop content
    fintech_results = await retriever.semantic_search("fintech payments B2B")
    assert len(fintech_results) >= 1
    fintech_texts = [r.chunk.text for r in fintech_results[:3]]
    assert any("PayLoop" in t or "payment" in t for t in fintech_texts)

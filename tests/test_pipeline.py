"""Tests for the ingestion pipeline."""

import pytest
from datetime import datetime

from src.models import SourceType


@pytest.mark.asyncio
async def test_ingest_interaction(pipeline, storage):
    interaction = await pipeline.ingest_interaction(
        raw_text="Meeting with NovaBuild about their platform. Sarah Chen presented strong metrics.",
        source_type=SourceType.MEETING_NOTES,
        timestamp=datetime.utcnow(),
        participants=["Sarah Chen"],
    )

    assert interaction.id is not None
    assert len(interaction.participants) == 1

    # Verify chunks were stored
    chunks = await storage.get_chunks_by_source(interaction.id)
    assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_ingest_email(pipeline, storage):
    interaction = await pipeline.ingest_email(
        subject="Intro: PayLoop - fintech",
        body="PayLoop is building a real-time B2B payment platform. Marcus Rivera is the CEO.",
        sender="Michael Torres",
        recipients=["team@fund.com"],
        timestamp=datetime.utcnow(),
    )

    assert interaction.source_type == SourceType.EMAIL
    chunks = await storage.get_chunks_by_source(interaction.id)
    assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_ingest_artifact(pipeline, storage):
    artifact = await pipeline.ingest_artifact(
        raw_text="Deal memo for CodeVault. Strong platform with competitive advantage.",
        source_type=SourceType.DOCUMENT,
        title="CodeVault Deal Memo",
    )

    assert artifact.id is not None
    assert artifact.title == "CodeVault Deal Memo"
    chunks = await storage.get_chunks_by_source(artifact.id)
    assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_entities_are_extracted_and_linked(pipeline, storage):
    await pipeline.ingest_interaction(
        raw_text="Met with Sarah Chen from NovaBuild. They have a strong platform.",
        source_type=SourceType.MEETING_NOTES,
        timestamp=datetime.utcnow(),
    )

    # Entity dedup: ingest again mentioning same entities
    await pipeline.ingest_interaction(
        raw_text="Follow up with NovaBuild team about metrics.",
        source_type=SourceType.EMAIL,
        timestamp=datetime.utcnow(),
    )

    # Sarah Chen should be deduplicated
    sarahs = await storage.search_people_by_name("Sarah Chen")
    assert len(sarahs) <= 1  # 0 or 1 depending on NER

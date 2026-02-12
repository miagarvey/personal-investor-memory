"""Shared test fixtures."""

import json
import os
import re
import tempfile
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.storage.relational import RelationalStore
from src.storage.vector import VectorStore, VectorStoreConfig
from src.embeddings import EmbeddingService
from src.entities.extractor import EntityExtractor
from src.entities.linker import EntityLinker
from src.ingestion.pipeline import IngestionPipeline

# Simple name-pattern heuristics used by the fake LLM in tests.
# Matches "FirstName LastName" patterns (two+ capitalized words).
_PERSON_PATTERN = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')

# Known test company names that appear across the test suite.
_KNOWN_COMPANIES = {
    "NovaBuild", "PayLoop", "CodeVault", "Google", "Microsoft",
    "Fivetran", "Scale AI", "Stripe", "Instabase",
    # Synthetic data companies
    "Anyscale", "Databricks", "Weaviate", "Snorkel AI",
    "Hugging Face", "Domino Data Lab", "Cohere",
}


def _fake_llm_extract(text: str) -> tuple[list[str], list[str]]:
    """Simple pattern-based extraction that mimics what the LLM would return."""
    companies = []
    for name in _KNOWN_COMPANIES:
        if name.lower() in text.lower():
            companies.append(name)

    people = []
    for match in _PERSON_PATTERN.finditer(text):
        candidate = match.group(1)
        # Skip if it matches a known company
        if candidate in _KNOWN_COMPANIES:
            continue
        if candidate not in people:
            people.append(candidate)

    return companies, people


@pytest_asyncio.fixture
async def storage(tmp_path):
    """Provide a fresh in-memory relational store for each test."""
    store = RelationalStore("sqlite+aiosqlite:///:memory:")
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def vector_store(tmp_path):
    """Provide a fresh vector store for each test."""
    config = VectorStoreConfig(
        collection_name="test_collection",
        embedding_dimension=384,
        persist_directory=str(tmp_path / "chroma"),
    )
    vs = VectorStore(config)
    yield vs


@pytest.fixture
def embedding_service():
    """Provide the local embedding service."""
    return EmbeddingService(backend="local")


@pytest.fixture
def entity_extractor():
    """Provide the entity extractor with a mocked LLM backend for tests."""
    extractor = EntityExtractor(api_key="test-key")

    async def _mock_extract_with_llm(text: str):
        return _fake_llm_extract(text)

    extractor._extract_with_llm = _mock_extract_with_llm
    return extractor


@pytest_asyncio.fixture
async def entity_linker(storage):
    """Provide the entity linker."""
    return EntityLinker(storage)


@pytest_asyncio.fixture
async def pipeline(storage, vector_store, embedding_service, entity_extractor, entity_linker):
    """Provide a fully wired ingestion pipeline."""
    return IngestionPipeline(
        storage=storage,
        entity_extractor=entity_extractor,
        entity_linker=entity_linker,
        vector_store=vector_store,
        embedding_service=embedding_service,
    )

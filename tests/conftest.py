"""Shared test fixtures."""

import os
import tempfile

import pytest
import pytest_asyncio

from src.storage.relational import RelationalStore
from src.storage.vector import VectorStore, VectorStoreConfig
from src.embeddings import EmbeddingService
from src.entities.extractor import EntityExtractor
from src.entities.linker import EntityLinker
from src.ingestion.pipeline import IngestionPipeline


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
    """Provide the entity extractor."""
    return EntityExtractor()


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

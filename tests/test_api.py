"""Tests for FastAPI endpoints."""

import pytest
import pytest_asyncio
import tempfile
import shutil
from httpx import AsyncClient, ASGITransport

from src.storage.relational import RelationalStore
from src.storage.vector import VectorStore, VectorStoreConfig
from src.embeddings import EmbeddingService
from src.entities.extractor import EntityExtractor
from src.entities.linker import EntityLinker
from src.ingestion.pipeline import IngestionPipeline
from src.search.retriever import Retriever
from src.models import SourceType
from src.api.routes import (
    IngestEmailRequest, IngestMeetingRequest, IngestDocumentRequest,
    IngestTextRequest, ChunkResponse, SearchResultResponse, ContextResponse
)


@pytest_asyncio.fixture
async def api_deps(tmp_path):
    """Set up all API dependencies for testing."""
    storage = RelationalStore("sqlite+aiosqlite:///:memory:")
    await storage.initialize()

    vector_store = VectorStore(VectorStoreConfig(
        collection_name="api_test",
        embedding_dimension=384,
        persist_directory=str(tmp_path / "chroma"),
    ))
    embedding_service = EmbeddingService(backend="local")
    extractor = EntityExtractor()
    linker = EntityLinker(storage)

    pipeline = IngestionPipeline(
        storage=storage,
        entity_extractor=extractor,
        entity_linker=linker,
        vector_store=vector_store,
        embedding_service=embedding_service,
    )

    retriever = Retriever(
        storage=storage,
        vector_store=vector_store,
        embedding_fn=embedding_service.embed,
    )

    yield {
        "storage": storage,
        "vector_store": vector_store,
        "embedding_service": embedding_service,
        "pipeline": pipeline,
        "retriever": retriever,
    }

    await storage.close()


@pytest.mark.asyncio
async def test_ingest_email_via_pipeline(api_deps):
    """Test email ingestion through the pipeline."""
    pipeline = api_deps["pipeline"]
    storage = api_deps["storage"]

    interaction = await pipeline.ingest_email(
        subject="Test Email",
        body="This is a test email about NovaBuild enterprise SaaS platform.",
        sender="Alice Smith",
        recipients=["Bob Jones"],
        timestamp=__import__("datetime").datetime.utcnow(),
    )

    assert interaction.id is not None
    chunks = await storage.get_chunks_by_source(interaction.id)
    assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_ingest_meeting_via_pipeline(api_deps):
    """Test meeting notes ingestion through the pipeline."""
    pipeline = api_deps["pipeline"]

    interaction = await pipeline.ingest_meeting_notes(
        notes="Met with Sarah Chen from NovaBuild about their developer tools platform.",
        meeting_title="Pitch Meeting",
        attendees=["Sarah Chen", "Michael Torres"],
        timestamp=__import__("datetime").datetime.utcnow(),
    )

    assert interaction.id is not None
    assert interaction.source_type == SourceType.MEETING_NOTES


@pytest.mark.asyncio
async def test_ingest_text_via_pipeline(api_deps):
    """Test freeform text ingestion through the pipeline."""
    pipeline = api_deps["pipeline"]

    artifact = await pipeline.ingest_artifact(
        raw_text="NovaBuild has strong product-market fit in the enterprise SaaS space.",
        source_type=SourceType.DOCUMENT,
        title="Quick Note",
    )

    assert artifact.id is not None


@pytest.mark.asyncio
async def test_search_via_retriever(api_deps):
    """Test semantic search through the retriever."""
    pipeline = api_deps["pipeline"]
    retriever = api_deps["retriever"]

    await pipeline.ingest_artifact(
        raw_text="PayLoop is building a fintech payments platform with strong unit economics.",
        source_type=SourceType.DOCUMENT,
    )

    results = await retriever.semantic_search("fintech payments")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_company_context_not_found(api_deps):
    """Test company context returns empty for non-existent company."""
    storage = api_deps["storage"]
    from uuid import UUID

    company = await storage.get_company(UUID("00000000-0000-0000-0000-000000000000"))
    assert company is None

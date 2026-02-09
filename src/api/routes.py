"""
FastAPI routes for Phase 1 Memory Core.

Endpoints:
- POST /ingest/email - Ingest an email
- POST /ingest/meeting - Ingest meeting notes
- POST /ingest/document - Ingest a document
- POST /ingest/text - Ingest freeform text
- GET /search - Semantic search
- GET /company/{id}/context - Get all context for a company
- GET /person/{id}/context - Get all context for a person
- POST /admin/seed - Seed database with synthetic data
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.storage.relational import RelationalStore
from src.storage.vector import VectorStore, VectorStoreConfig
from src.embeddings import EmbeddingService
from src.entities.extractor import EntityExtractor
from src.entities.linker import EntityLinker
from src.ingestion.pipeline import IngestionPipeline
from src.search.retriever import Retriever
from src.models import SourceType


# === Request/Response Models ===

class IngestEmailRequest(BaseModel):
    subject: str
    body: str
    sender: str
    recipients: list[str]
    timestamp: datetime
    thread_id: Optional[str] = None


class IngestMeetingRequest(BaseModel):
    title: str
    notes: str
    attendees: list[str]
    timestamp: datetime


class IngestDocumentRequest(BaseModel):
    title: str
    content: str
    timestamp: Optional[datetime] = None


class IngestTextRequest(BaseModel):
    text: str
    source_type: str = "document"
    title: Optional[str] = None
    timestamp: Optional[datetime] = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    company_id: Optional[UUID] = None
    person_id: Optional[UUID] = None


class ChunkResponse(BaseModel):
    id: UUID
    text: str
    source_type: str
    timestamp: datetime


class SearchResultResponse(BaseModel):
    chunk: ChunkResponse
    score: float
    company_name: Optional[str] = None
    people_names: Optional[list[str]] = None


class ContextResponse(BaseModel):
    entity_name: str
    results: list[SearchResultResponse]


# === Dependency container ===

class AppState:
    storage: RelationalStore
    vector_store: VectorStore
    embedding_service: EmbeddingService
    pipeline: IngestionPipeline
    retriever: Retriever


# === App Factory ===

def create_app() -> FastAPI:
    """Create FastAPI application with all dependencies wired up."""

    state = AppState()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Initialize storage
        state.storage = RelationalStore("sqlite+aiosqlite:///investor_memory.db")
        await state.storage.initialize()

        state.vector_store = VectorStore(VectorStoreConfig(embedding_dimension=384))
        state.embedding_service = EmbeddingService(backend="local")

        extractor = EntityExtractor()
        linker = EntityLinker(state.storage)

        state.pipeline = IngestionPipeline(
            storage=state.storage,
            entity_extractor=extractor,
            entity_linker=linker,
            vector_store=state.vector_store,
            embedding_service=state.embedding_service,
        )

        state.retriever = Retriever(
            storage=state.storage,
            vector_store=state.vector_store,
            embedding_fn=state.embedding_service.embed,
        )

        yield

        await state.storage.close()

    app = FastAPI(
        title="Investor Memory - Phase 1",
        description="Memory Core: Ingestion, Entity Extraction, Search",
        version="0.1.0",
        lifespan=lifespan,
    )

    def _search_result_to_response(sr) -> SearchResultResponse:
        return SearchResultResponse(
            chunk=ChunkResponse(
                id=sr.chunk.id,
                text=sr.chunk.text,
                source_type=sr.chunk.source_type.value,
                timestamp=sr.chunk.created_at,
            ),
            score=sr.score,
            company_name=sr.company.name if sr.company else None,
            people_names=[p.name for p in sr.people] if sr.people else None,
        )

    @app.post("/ingest/email")
    async def ingest_email(request: IngestEmailRequest):
        """Ingest an email into the memory system."""
        interaction = await state.pipeline.ingest_email(
            subject=request.subject,
            body=request.body,
            sender=request.sender,
            recipients=request.recipients,
            timestamp=request.timestamp,
            thread_id=request.thread_id,
        )
        return {"status": "ok", "interaction_id": str(interaction.id)}

    @app.post("/ingest/meeting")
    async def ingest_meeting(request: IngestMeetingRequest):
        """Ingest meeting notes."""
        interaction = await state.pipeline.ingest_meeting_notes(
            notes=request.notes,
            meeting_title=request.title,
            attendees=request.attendees,
            timestamp=request.timestamp,
        )
        return {"status": "ok", "interaction_id": str(interaction.id)}

    @app.post("/ingest/document")
    async def ingest_document(request: IngestDocumentRequest):
        """Ingest a document."""
        artifact = await state.pipeline.ingest_artifact(
            raw_text=request.content,
            source_type=SourceType.DOCUMENT,
            title=request.title,
            timestamp=request.timestamp,
        )
        return {"status": "ok", "artifact_id": str(artifact.id)}

    @app.post("/ingest/text")
    async def ingest_text(request: IngestTextRequest):
        """Ingest freeform text."""
        source_map = {
            "email": SourceType.EMAIL,
            "meeting_notes": SourceType.MEETING_NOTES,
            "document": SourceType.DOCUMENT,
            "newsletter": SourceType.NEWSLETTER,
            "twitter": SourceType.TWITTER,
        }
        source_type = source_map.get(request.source_type, SourceType.DOCUMENT)

        artifact = await state.pipeline.ingest_artifact(
            raw_text=request.text,
            source_type=source_type,
            title=request.title,
            timestamp=request.timestamp,
        )
        return {"status": "ok", "artifact_id": str(artifact.id)}

    @app.get("/search")
    async def search(
        query: str,
        limit: int = 10,
        company_id: Optional[UUID] = None,
        person_id: Optional[UUID] = None,
    ) -> list[SearchResultResponse]:
        """Semantic search over all ingested content."""
        results = await state.retriever.semantic_search(
            query=query,
            limit=limit,
            filter_company_id=company_id,
            filter_person_id=person_id,
        )
        return [_search_result_to_response(r) for r in results]

    @app.get("/company/{company_id}/context")
    async def get_company_context(company_id: UUID) -> ContextResponse:
        """Get all past discussions related to a company."""
        company = await state.storage.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        results = await state.retriever.search_by_company(company_id)
        return ContextResponse(
            entity_name=company.name,
            results=[_search_result_to_response(r) for r in results],
        )

    @app.get("/person/{person_id}/context")
    async def get_person_context(person_id: UUID) -> ContextResponse:
        """Get all interactions involving a person."""
        person = await state.storage.get_person(person_id)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        results = await state.retriever.search_by_person(person_id)
        return ContextResponse(
            entity_name=person.name,
            results=[_search_result_to_response(r) for r in results],
        )

    @app.post("/admin/seed")
    async def seed_database():
        """Seed the database with synthetic data."""
        from src.data.synthetic import SyntheticDataGenerator
        generator = SyntheticDataGenerator()
        count = await generator.seed_database(state.pipeline)
        return {"status": "ok", "items_seeded": count}

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    return app


# For running directly
app = create_app()

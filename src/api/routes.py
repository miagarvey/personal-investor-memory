"""
FastAPI routes for Investor Memory.

Phase 1 endpoints:
- POST /ingest/email - Ingest an email
- POST /ingest/meeting - Ingest meeting notes
- POST /ingest/document - Ingest a document
- POST /ingest/text - Ingest freeform text
- GET /search - Semantic search
- GET /company/{id}/context - Get all context for a company
- GET /person/{id}/context - Get all context for a person
- POST /admin/seed - Seed database with synthetic data

Phase 2 endpoints:
- GET /companies - List/search companies
- GET /people - List/search people
- POST /analyze - Analyze text (extract entities, find related)
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.storage.relational import RelationalStore
from src.storage.vector import VectorStore, VectorStoreConfig
from src.embeddings import EmbeddingService
from src.entities.extractor import EntityExtractor
from src.entities.linker import EntityLinker
from src.ingestion.pipeline import IngestionPipeline
from src.search.retriever import Retriever
from src.models import SourceType, EntityType


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


# Phase 2 models
class CompanyResponse(BaseModel):
    id: UUID
    name: str
    url: Optional[str] = None
    description: Optional[str] = None


class PersonResponse(BaseModel):
    id: UUID
    name: str
    email: Optional[str] = None
    company_name: Optional[str] = None


class ExtractedEntityResponse(BaseModel):
    type: str  # "company" or "person"
    name: str
    id: Optional[UUID] = None


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    extracted_entities: list[ExtractedEntityResponse]
    related_content: list[SearchResultResponse]


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
        title="Investor Memory",
        description="Memory Core: Ingestion, Entity Extraction, Search, Context Viewer",
        version="0.2.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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

    # === Phase 2: Context Viewer UI endpoints ===

    @app.get("/companies")
    async def list_companies(q: str = "", limit: int = 10) -> list[CompanyResponse]:
        """List/search companies."""
        if q:
            companies = await state.storage.search_companies_by_name(q, limit=limit)
        else:
            # Get all companies if no query
            companies = await state.storage.list_companies(limit=limit)
        return [
            CompanyResponse(
                id=c.id,
                name=c.name,
                url=c.url,
                description=c.description,
            )
            for c in companies
        ]

    @app.get("/people")
    async def list_people(q: str = "", limit: int = 10) -> list[PersonResponse]:
        """List/search people."""
        if q:
            people = await state.storage.search_people_by_name(q, limit=limit)
        else:
            people = await state.storage.list_people(limit=limit)

        responses = []
        for p in people:
            company_name = None
            if p.company_id:
                company = await state.storage.get_company(p.company_id)
                if company:
                    company_name = company.name
            responses.append(PersonResponse(
                id=p.id,
                name=p.name,
                email=p.email,
                company_name=company_name,
            ))
        return responses

    @app.post("/analyze")
    async def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
        """Analyze text: extract entities and find related content without saving."""
        # Extract entities
        extractor = EntityExtractor()

        raw_entities = await extractor.extract(request.text)
        extracted_entities = []

        for e in raw_entities:
            entity_type = "company" if e.entity_type == EntityType.COMPANY else "person"
            meta = e.metadata or {}

            # Try to find existing entity without creating new ones
            entity_id = None
            if entity_type == "company":
                if meta.get("linkedin_url"):
                    existing = await state.storage.get_company_by_linkedin(meta["linkedin_url"])
                    if existing:
                        entity_id = existing.id
                if not entity_id and meta.get("url"):
                    existing = await state.storage.get_company_by_url(meta["url"])
                    if existing:
                        entity_id = existing.id
                if not entity_id:
                    matches = await state.storage.search_companies_by_name(e.text, limit=1)
                    if matches:
                        entity_id = matches[0].id
            else:  # person
                if meta.get("linkedin_url"):
                    existing = await state.storage.get_person_by_linkedin(meta["linkedin_url"])
                    if existing:
                        entity_id = existing.id
                if not entity_id and meta.get("email"):
                    existing = await state.storage.get_person_by_email(meta["email"])
                    if existing:
                        entity_id = existing.id
                if not entity_id:
                    matches = await state.storage.search_people_by_name(e.text, limit=1)
                    if matches:
                        entity_id = matches[0].id

            extracted_entities.append(ExtractedEntityResponse(
                type=entity_type,
                name=e.text,
                id=entity_id,
            ))

        # Find related content via semantic search on the input text
        related = await state.retriever.semantic_search(
            query=request.text[:500],  # Use first 500 chars as query
            limit=10,
        )

        return AnalyzeResponse(
            extracted_entities=extracted_entities,
            related_content=[_search_result_to_response(r) for r in related],
        )

    @app.get("/")
    async def root():
        """Redirect to the UI."""
        return FileResponse(static_dir / "index.html")

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    return app


# For running directly
app = create_app()

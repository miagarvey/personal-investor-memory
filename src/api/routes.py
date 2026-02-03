"""
FastAPI routes for Phase 1 Memory Core.

Endpoints:
- POST /ingest/email - Ingest an email
- POST /ingest/meeting - Ingest meeting notes
- POST /ingest/document - Ingest a document
- GET /search - Semantic search
- GET /company/{id}/context - Get all context for a company
- GET /person/{id}/context - Get all context for a person
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


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


# === App Factory ===

def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Investor Memory - Phase 1",
        description="Memory Core: Ingestion, Entity Extraction, Search",
        version="0.1.0",
    )

    # TODO: Initialize dependencies (storage, pipeline, retriever)

    @app.post("/ingest/email")
    async def ingest_email(request: IngestEmailRequest):
        """Ingest an email into the memory system."""
        # TODO: Call ingestion pipeline
        raise HTTPException(status_code=501, detail="Not implemented")

    @app.post("/ingest/meeting")
    async def ingest_meeting(request: IngestMeetingRequest):
        """Ingest meeting notes."""
        # TODO: Call ingestion pipeline
        raise HTTPException(status_code=501, detail="Not implemented")

    @app.post("/ingest/document")
    async def ingest_document(request: IngestDocumentRequest):
        """Ingest a document."""
        # TODO: Call ingestion pipeline
        raise HTTPException(status_code=501, detail="Not implemented")

    @app.get("/search")
    async def search(
        query: str,
        limit: int = 10,
        company_id: Optional[UUID] = None,
        person_id: Optional[UUID] = None,
    ) -> list[SearchResultResponse]:
        """
        Semantic search over all ingested content.

        Optionally filter by company or person.
        """
        # TODO: Call retriever
        raise HTTPException(status_code=501, detail="Not implemented")

    @app.get("/company/{company_id}/context")
    async def get_company_context(company_id: UUID) -> ContextResponse:
        """Get all past discussions related to a company."""
        # TODO: Call retriever.search_by_company
        raise HTTPException(status_code=501, detail="Not implemented")

    @app.get("/person/{person_id}/context")
    async def get_person_context(person_id: UUID) -> ContextResponse:
        """Get all interactions involving a person."""
        # TODO: Call retriever.search_by_person
        raise HTTPException(status_code=501, detail="Not implemented")

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    return app


# For running directly
app = create_app()

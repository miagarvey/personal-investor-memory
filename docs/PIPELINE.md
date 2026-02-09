# Phase 1 Pipeline Documentation

## Overview

The Investor Memory system is a memory-augmented tool for investment analysts that surfaces relevant past context (conversations, documents, patterns) at the moment it's most useful. This document describes the Phase 1 implementation.

## Architecture

```
Raw Input (emails, meeting notes, documents, freeform text)
    │
    ▼
┌─────────────────┐
│  TextChunker    │  Split text into overlapping chunks (512 tokens, 50 overlap)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ EntityExtractor │  spaCy NER (ORG, PERSON) + URL/email/LinkedIn regex
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  EntityLinker   │  Deduplicate by URL/LinkedIn/email, fuzzy name match
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│EmbeddingService │  sentence-transformers/all-MiniLM-L6-v2 (384-dim)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│              Dual Storage               │
│  ┌─────────────────┐ ┌───────────────┐  │
│  │ RelationalStore │ │  VectorStore  │  │
│  │    (SQLite)     │ │  (ChromaDB)   │  │
│  └─────────────────┘ └───────────────┘  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│    Retriever    │  Entity-based + semantic search
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI API   │  REST endpoints for ingestion and search
└─────────────────┘
```

## Components

### 1. Text Chunker (`src/ingestion/chunker.py`)

Splits text into overlapping chunks for embedding and retrieval.

**Configuration:**
- `chunk_size`: 512 tokens (default)
- `chunk_overlap`: 50 tokens
- `min_chunk_size`: 100 tokens

**Behavior:**
- Approximates tokens as 4 characters each
- Tries to break at paragraph (`\n\n`) or sentence (`. `, `! `, `? `) boundaries
- Maintains overlap between chunks for context preservation

### 2. Entity Extractor (`src/entities/extractor.py`)

Extracts two types of entities from text:

**Companies:**
- spaCy NER with label `ORG`
- URL regex extraction (extracts company name from domain)
- LinkedIn company URL extraction (`linkedin.com/company/...`)

**People:**
- spaCy NER with label `PERSON`
- Email address extraction (derives name from `john.doe@...`)
- LinkedIn profile URL extraction (`linkedin.com/in/...`)

### 3. Entity Linker (`src/entities/linker.py`)

Deduplicates entities to canonical records:

**Matching Priority:**
1. LinkedIn URL (exact match)
2. Company URL / Email (exact match)
3. Fuzzy name match (SQL `LIKE %name%`)

If no match found, creates a new entity.

### 4. Embedding Service (`src/embeddings.py`)

Generates vector embeddings for semantic search.

**Default (Development):**
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Dimension: 384
- Local, no API key required

**Production (Optional):**
- Model: OpenAI `text-embedding-ada-002`
- Dimension: 1536
- Set `backend="openai"` and provide `api_key`

### 5. Storage Layer

**RelationalStore (`src/storage/relational.py`):**
- SQLAlchemy with async SQLite (`sqlite+aiosqlite:///`)
- Stores: Companies, People, Interactions, Artifacts, Chunks
- Handles entity relationships and metadata

**VectorStore (`src/storage/vector.py`):**
- ChromaDB with persistent storage
- Stores chunk embeddings with entity ID metadata
- Supports filtered semantic search

### 6. Retriever (`src/search/retriever.py`)

Two retrieval paths:

**Entity-based Search:**
- `search_by_company(company_id)` - All chunks mentioning a company
- `search_by_person(person_id)` - All chunks mentioning a person

**Semantic Search:**
- `semantic_search(query)` - Vector similarity search
- `find_related(query)` - Main entry point for "what do we know about X?"

## Data Models

### Entities

```python
Company:
  - id: UUID
  - name: str
  - url: Optional[str]
  - linkedin_url: Optional[str]
  - description: Optional[str]

Person:
  - id: UUID
  - name: str
  - email: Optional[str]
  - linkedin_url: Optional[str]
  - company_id: Optional[UUID]
```

### Content

```python
Interaction:  # Emails, meetings, conversations
  - id: UUID
  - source_type: email | meeting_notes | newsletter | twitter
  - raw_text: str
  - timestamp: datetime
  - participants: list[UUID]  # Person IDs
  - metadata: dict

Artifact:  # Documents, memos, decks
  - id: UUID
  - source_type: document
  - raw_text: str
  - title: Optional[str]
  - timestamp: datetime
  - related_companies: list[UUID]

Chunk:  # Embedded text segments
  - id: UUID
  - text: str
  - source_id: UUID
  - source_type: SourceType
  - entity_ids: list[UUID]
  - embedding: list[float]
```

## API Endpoints

### Ingestion

**POST /ingest/email**
```json
{
  "subject": "Intro: NovaBuild - construction tech",
  "body": "NovaBuild is building...",
  "sender": "Michael Torres",
  "recipients": ["team@fund.com"],
  "timestamp": "2024-01-15T10:00:00",
  "thread_id": "optional-thread-id"
}
```

**POST /ingest/meeting**
```json
{
  "title": "First Meeting: NovaBuild",
  "notes": "Meeting with Sarah Chen...",
  "attendees": ["Sarah Chen", "Michael Torres"],
  "timestamp": "2024-01-15T14:00:00"
}
```

**POST /ingest/document**
```json
{
  "title": "NovaBuild Deal Memo",
  "content": "# Executive Summary...",
  "timestamp": "2024-01-15T10:00:00"
}
```

**POST /ingest/text** (freeform)
```json
{
  "text": "Quick note about NovaBuild...",
  "source_type": "document",
  "title": "Optional title"
}
```

### Search

**GET /search?query=construction+platform&limit=10**

Returns semantically similar content:
```json
[
  {
    "chunk": {
      "id": "uuid",
      "text": "NovaBuild's platform has strong adoption...",
      "source_type": "meeting_notes",
      "timestamp": "2024-01-15T14:00:00"
    },
    "score": 0.85,
    "company_name": "NovaBuild",
    "people_names": ["Sarah Chen"]
  }
]
```

**GET /company/{company_id}/context**

Returns all content related to a company.

**GET /person/{person_id}/context**

Returns all content involving a person.

### Admin

**POST /admin/seed**

Seeds the database with 50 synthetic VC-domain items (10 companies × 5 document types).

**GET /health**

Health check endpoint.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Run tests
pytest tests/ -v

# Start the server
uvicorn src.api.routes:app --reload

# Seed with synthetic data
curl -X POST http://localhost:8000/admin/seed

# Search for content
curl "http://localhost:8000/search?query=construction+platform"

# Ingest an email
curl -X POST http://localhost:8000/ingest/email \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Intro: NewCo",
    "body": "NewCo is building a fintech platform...",
    "sender": "Jane Doe",
    "recipients": ["team@fund.com"],
    "timestamp": "2024-01-20T10:00:00"
  }'
```

## Configuration

**Environment Variables (`.env`):**
```
DATABASE_URL=sqlite+aiosqlite:///investor_memory.db
OPENAI_API_KEY=sk-...  # Only if using OpenAI embeddings
```

**Embedding Backend:**
```python
# Local (default, free)
EmbeddingService(backend="local")

# OpenAI (production)
EmbeddingService(backend="openai", api_key="sk-...")
```

## File Structure

```
src/
├── api/
│   └── routes.py          # FastAPI endpoints
├── data/
│   └── synthetic.py       # Synthetic data generator
├── embeddings.py          # Embedding service
├── entities/
│   ├── extractor.py       # spaCy NER + regex
│   └── linker.py          # Entity deduplication
├── ingestion/
│   ├── chunker.py         # Text chunking
│   └── pipeline.py        # Main ingestion pipeline
├── models/
│   └── base.py            # Domain models
├── search/
│   └── retriever.py       # Search interface
└── storage/
    ├── base.py            # Abstract storage interface
    ├── models.py          # SQLAlchemy ORM models
    ├── relational.py      # SQLite storage
    └── vector.py          # ChromaDB storage

tests/
├── conftest.py            # Shared fixtures
├── test_*.py              # Test files (47 tests total)

scripts/
└── seed_data.py           # CLI seeding script
```

## Next Steps (Future Phases)

- **Phase 2:** Context Viewer web UI
- **Phase 3:** Claim extraction (assertions with polarity/scope/source)
- **Phase 4:** Pattern aggregation and time awareness
- **Phase 5:** Partner pilots and evaluation

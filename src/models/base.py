from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class SourceType(Enum):
    EMAIL = "email"
    MEETING_NOTES = "meeting_notes"
    DOCUMENT = "document"
    NEWSLETTER = "newsletter"
    TWITTER = "twitter"


class EntityType(Enum):
    COMPANY = "company"
    PERSON = "person"
    THEME = "theme"


@dataclass
class Entity:
    """Base class for extracted entities."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    entity_type: EntityType = EntityType.COMPANY
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Company(Entity):
    """A company entity, normalized by URL or LinkedIn URL."""
    entity_type: EntityType = field(default=EntityType.COMPANY, init=False)
    url: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Person(Entity):
    """A person entity, normalized by LinkedIn URL."""
    entity_type: EntityType = field(default=EntityType.PERSON, init=False)
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    company_id: Optional[UUID] = None  # Link to associated company


@dataclass
class Theme(Entity):
    """An investment theme or pattern."""
    entity_type: EntityType = field(default=EntityType.THEME, init=False)
    keywords: list[str] = field(default_factory=list)


@dataclass
class Interaction:
    """A conversation or interaction (email, meeting, etc.)."""
    id: UUID = field(default_factory=uuid4)
    source_type: SourceType = SourceType.EMAIL
    raw_text: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    participants: list[UUID] = field(default_factory=list)  # Person IDs
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Artifact:
    """A document or artifact (deck, memo, etc.)."""
    id: UUID = field(default_factory=uuid4)
    source_type: SourceType = SourceType.DOCUMENT
    raw_text: str = ""
    title: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    related_companies: list[UUID] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Chunk:
    """A text chunk for embedding and retrieval."""
    id: UUID = field(default_factory=uuid4)
    text: str = ""
    source_id: UUID = field(default_factory=uuid4)  # Interaction or Artifact ID
    source_type: SourceType = SourceType.EMAIL
    entity_ids: list[UUID] = field(default_factory=list)  # Linked entities
    embedding: Optional[list[float]] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

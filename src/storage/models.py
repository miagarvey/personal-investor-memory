"""SQLAlchemy ORM models for the investor memory relational store."""

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, DateTime, Float, ForeignKey, Table, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _new_uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


# === Association tables ===

interaction_participants = Table(
    "interaction_participants",
    Base.metadata,
    Column("interaction_id", String(36), ForeignKey("interactions.id"), primary_key=True),
    Column("person_id", String(36), ForeignKey("people.id"), primary_key=True),
)

chunk_entities = Table(
    "chunk_entities",
    Base.metadata,
    Column("chunk_id", String(36), ForeignKey("chunks.id"), primary_key=True),
    Column("entity_id", String(36), primary_key=True),
    Column("entity_type", String(20)),  # company, person, theme
)

artifact_companies = Table(
    "artifact_companies",
    Base.metadata,
    Column("artifact_id", String(36), ForeignKey("artifacts.id"), primary_key=True),
    Column("company_id", String(36), ForeignKey("companies.id"), primary_key=True),
)


# === Entity tables ===

class CompanyRow(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    name = Column(String(255), nullable=False, index=True)
    url = Column(String(512), unique=True, nullable=True)
    linkedin_url = Column(String(512), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PersonRow(Base):
    __tablename__ = "people"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    name = Column(String(255), nullable=False, index=True)
    linkedin_url = Column(String(512), unique=True, nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("CompanyRow", backref="people")


class ThemeRow(Base):
    __tablename__ = "themes"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    name = Column(String(255), nullable=False, unique=True, index=True)
    keywords_json = Column(Text, default="[]")  # JSON list of keywords
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def keywords(self) -> list[str]:
        return json.loads(self.keywords_json) if self.keywords_json else []

    @keywords.setter
    def keywords(self, value: list[str]):
        self.keywords_json = json.dumps(value)


# === Interaction / Artifact / Chunk tables ===

class InteractionRow(Base):
    __tablename__ = "interactions"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    source_type = Column(String(50), nullable=False)
    raw_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    participants = relationship("PersonRow", secondary=interaction_participants, backref="interactions")

    @property
    def metadata_dict(self) -> dict:
        return json.loads(self.metadata_json) if self.metadata_json else {}

    @metadata_dict.setter
    def metadata_dict(self, value: dict):
        self.metadata_json = json.dumps(value)


class ArtifactRow(Base):
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    source_type = Column(String(50), nullable=False)
    raw_text = Column(Text, nullable=False)
    title = Column(String(512), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    related_companies = relationship("CompanyRow", secondary=artifact_companies)

    @property
    def metadata_dict(self) -> dict:
        return json.loads(self.metadata_json) if self.metadata_json else {}

    @metadata_dict.setter
    def metadata_dict(self, value: dict):
        self.metadata_json = json.dumps(value)


class ChunkRow(Base):
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    text = Column(Text, nullable=False)
    source_id = Column(String(36), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_chunks_source", "source_id", "source_type"),
    )

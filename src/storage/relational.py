from typing import Optional
from uuid import UUID

from src.models import (
    Interaction, Artifact, Chunk,
    Company, Person, Theme
)
from src.storage.base import StorageBackend


class RelationalStore(StorageBackend):
    """
    Relational database storage for entities and metadata.

    Handles:
    - Entity storage and lookup
    - Interaction/artifact metadata
    - Relationships between entities

    Options:
    - SQLite (local development)
    - PostgreSQL (production)
    """

    def __init__(self, connection_string: str = "sqlite:///investor_memory.db"):
        self.connection_string = connection_string
        # TODO: Initialize SQLAlchemy engine and session

    # === Interactions ===

    async def save_interaction(self, interaction: Interaction) -> None:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError

    async def get_interaction(self, id: UUID) -> Optional[Interaction]:
        raise NotImplementedError

    async def get_interactions_by_participant(
        self, person_id: UUID, limit: int = 50
    ) -> list[Interaction]:
        raise NotImplementedError

    # === Artifacts ===

    async def save_artifact(self, artifact: Artifact) -> None:
        raise NotImplementedError

    async def get_artifact(self, id: UUID) -> Optional[Artifact]:
        raise NotImplementedError

    # === Chunks ===

    async def save_chunk(self, chunk: Chunk) -> None:
        raise NotImplementedError

    async def get_chunks_by_source(self, source_id: UUID) -> list[Chunk]:
        raise NotImplementedError

    # === Companies ===

    async def save_company(self, company: Company) -> None:
        raise NotImplementedError

    async def get_company(self, id: UUID) -> Optional[Company]:
        raise NotImplementedError

    async def get_company_by_url(self, url: str) -> Optional[Company]:
        raise NotImplementedError

    async def get_company_by_linkedin(self, linkedin_url: str) -> Optional[Company]:
        raise NotImplementedError

    async def search_companies_by_name(
        self, name: str, limit: int = 5
    ) -> list[Company]:
        raise NotImplementedError

    # === People ===

    async def save_person(self, person: Person) -> None:
        raise NotImplementedError

    async def get_person(self, id: UUID) -> Optional[Person]:
        raise NotImplementedError

    async def get_person_by_email(self, email: str) -> Optional[Person]:
        raise NotImplementedError

    async def get_person_by_linkedin(self, linkedin_url: str) -> Optional[Person]:
        raise NotImplementedError

    async def search_people_by_name(
        self, name: str, limit: int = 5
    ) -> list[Person]:
        raise NotImplementedError

    # === Themes ===

    async def save_theme(self, theme: Theme) -> None:
        raise NotImplementedError

    async def get_theme(self, id: UUID) -> Optional[Theme]:
        raise NotImplementedError

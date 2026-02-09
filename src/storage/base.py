from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.models import (
    Interaction, Artifact, Chunk,
    Company, Person, Theme, Entity
)


class StorageBackend(ABC):
    """
    Abstract storage backend combining vector and relational storage.

    Phase 1 uses vector + relational for:
    - Entity-based retrieval (relational)
    - Semantic search (vector)
    """

    # === Interactions ===

    @abstractmethod
    async def save_interaction(self, interaction: Interaction) -> None:
        """Save an interaction."""
        pass

    @abstractmethod
    async def get_interaction(self, id: UUID) -> Optional[Interaction]:
        """Get interaction by ID."""
        pass

    @abstractmethod
    async def get_interactions_by_participant(
        self, person_id: UUID, limit: int = 50
    ) -> list[Interaction]:
        """Get interactions involving a person."""
        pass

    # === Artifacts ===

    @abstractmethod
    async def save_artifact(self, artifact: Artifact) -> None:
        """Save an artifact."""
        pass

    @abstractmethod
    async def get_artifact(self, id: UUID) -> Optional[Artifact]:
        """Get artifact by ID."""
        pass

    # === Chunks ===

    @abstractmethod
    async def save_chunk(self, chunk: Chunk) -> None:
        """Save a chunk with its embedding."""
        pass

    @abstractmethod
    async def get_chunks_by_source(self, source_id: UUID) -> list[Chunk]:
        """Get all chunks from a source."""
        pass

    # === Entities ===

    @abstractmethod
    async def save_company(self, company: Company) -> None:
        pass

    @abstractmethod
    async def get_company(self, id: UUID) -> Optional[Company]:
        pass

    @abstractmethod
    async def get_company_by_url(self, url: str) -> Optional[Company]:
        pass

    @abstractmethod
    async def get_company_by_linkedin(self, linkedin_url: str) -> Optional[Company]:
        pass

    @abstractmethod
    async def search_companies_by_name(
        self, name: str, limit: int = 5
    ) -> list[Company]:
        pass

    @abstractmethod
    async def save_person(self, person: Person) -> None:
        pass

    @abstractmethod
    async def get_person(self, id: UUID) -> Optional[Person]:
        pass

    @abstractmethod
    async def get_person_by_email(self, email: str) -> Optional[Person]:
        pass

    @abstractmethod
    async def get_person_by_linkedin(self, linkedin_url: str) -> Optional[Person]:
        pass

    @abstractmethod
    async def search_people_by_name(
        self, name: str, limit: int = 5
    ) -> list[Person]:
        pass

    @abstractmethod
    async def save_theme(self, theme: Theme) -> None:
        pass

    @abstractmethod
    async def get_theme(self, id: UUID) -> Optional[Theme]:
        pass

    @abstractmethod
    async def get_theme_by_name(self, name: str) -> Optional[Theme]:
        """Get a theme by its name."""
        pass

    @abstractmethod
    async def get_chunks_by_entity(self, entity_id: UUID, limit: int = 50) -> list[Chunk]:
        """Get all chunks linked to a specific entity."""
        pass

from typing import Optional
from uuid import UUID

from src.models import Entity, Company, Person, EntityType
from src.entities.extractor import ExtractedEntity
from src.storage.base import StorageBackend


class EntityLinker:
    """
    Links extracted entity mentions to canonical entities.

    Handles:
    - Deduplication (same entity mentioned different ways)
    - Normalization (LinkedIn URL as canonical ID)
    - Creating new entities when no match found
    """

    def __init__(self, storage: StorageBackend):
        self.storage = storage

    async def link_entity(self, extracted: ExtractedEntity) -> Entity:
        """
        Link an extracted mention to a canonical entity.

        Routes to the appropriate linker based on entity type.
        Returns existing entity if found, creates new one otherwise.
        """
        meta = extracted.metadata or {}

        if extracted.entity_type == EntityType.COMPANY:
            return await self.link_company(
                name=extracted.text,
                url=meta.get("url"),
                linkedin_url=meta.get("linkedin_url"),
            )
        elif extracted.entity_type == EntityType.PERSON:
            return await self.link_person(
                name=extracted.text,
                email=meta.get("email"),
                linkedin_url=meta.get("linkedin_url"),
            )
        else:
            raise ValueError(f"Unknown entity type: {extracted.entity_type}")

    async def link_company(
        self,
        name: str,
        url: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> Company:
        """Link or create a company entity."""
        # Prefer LinkedIn URL for matching, then domain URL
        if linkedin_url:
            existing = await self.storage.get_company_by_linkedin(linkedin_url)
            if existing:
                return existing

        if url:
            existing = await self.storage.get_company_by_url(url)
            if existing:
                return existing

        # Fuzzy name match as fallback
        existing = await self.storage.search_companies_by_name(name)
        if existing:
            return existing[0]  # Return best match

        # Create new company
        company = Company(name=name, url=url, linkedin_url=linkedin_url)
        await self.storage.save_company(company)
        return company

    async def link_person(
        self,
        name: str,
        email: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> Person:
        """Link or create a person entity."""
        if linkedin_url:
            existing = await self.storage.get_person_by_linkedin(linkedin_url)
            if existing:
                return existing

        if email:
            existing = await self.storage.get_person_by_email(email)
            if existing:
                return existing

        # Fuzzy name match
        existing = await self.storage.search_people_by_name(name)
        if existing:
            return existing[0]

        person = Person(name=name, email=email, linkedin_url=linkedin_url)
        await self.storage.save_person(person)
        return person

from dataclasses import dataclass
from typing import Optional

from src.models import Entity, Company, Person, Theme, EntityType


@dataclass
class ExtractedEntity:
    """An entity extracted from text, before linking."""
    text: str  # The mention as it appears in text
    entity_type: EntityType
    start_pos: int
    end_pos: int
    confidence: float = 1.0
    metadata: dict | None = None


class EntityExtractor:
    """
    Extracts entities (companies, people, themes) from text.

    Phase 1 implementation options:
    - Rule-based extraction (patterns, keywords)
    - spaCy NER
    - LLM-based extraction
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        # TODO: Initialize extraction model

    def extract(self, text: str) -> list[ExtractedEntity]:
        """
        Extract all entities from text.

        Returns entities with their positions and types.
        """
        # TODO: Implement entity extraction
        # Options:
        # 1. spaCy for NER (ORG, PERSON)
        # 2. LLM prompt for more nuanced extraction
        # 3. Regex patterns for URLs, email addresses
        raise NotImplementedError

    def extract_companies(self, text: str) -> list[ExtractedEntity]:
        """Extract company mentions."""
        # TODO: Look for:
        # - Organization names (NER)
        # - Company URLs
        # - LinkedIn company URLs
        raise NotImplementedError

    def extract_people(self, text: str) -> list[ExtractedEntity]:
        """Extract person mentions."""
        # TODO: Look for:
        # - Person names (NER)
        # - Email addresses -> extract name
        # - LinkedIn profile URLs
        raise NotImplementedError

    def extract_themes(self, text: str) -> list[ExtractedEntity]:
        """Extract investment themes/patterns."""
        # TODO: This is more nuanced - likely needs LLM
        # Examples: "enterprise SaaS", "developer tools", "TAM concerns"
        raise NotImplementedError

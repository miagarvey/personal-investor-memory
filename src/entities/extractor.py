import re
from dataclasses import dataclass

import spacy

from src.models import EntityType


@dataclass
class ExtractedEntity:
    """An entity extracted from text, before linking."""
    text: str  # The mention as it appears in text
    entity_type: EntityType
    start_pos: int
    end_pos: int
    confidence: float = 1.0
    metadata: dict | None = None


# Regex patterns
URL_PATTERN = re.compile(
    r'https?://(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z]{2,})+)(?:/[^\s]*)?'
)
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
)
LINKEDIN_COMPANY_PATTERN = re.compile(
    r'linkedin\.com/company/([a-zA-Z0-9-]+)'
)
LINKEDIN_PERSON_PATTERN = re.compile(
    r'linkedin\.com/in/([a-zA-Z0-9-]+)'
)


class EntityExtractor:
    """
    Extracts entities (companies and people) from text.

    Uses spaCy NER for ORG/PERSON + regex for URLs/emails/LinkedIn.
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.nlp = spacy.load(model_name)

    def extract(self, text: str) -> list[ExtractedEntity]:
        """Extract all entities (companies and people) from text."""
        entities = []
        entities.extend(self.extract_companies(text))
        entities.extend(self.extract_people(text))
        return entities

    def extract_companies(self, text: str) -> list[ExtractedEntity]:
        """Extract company mentions using spaCy ORG + URL/LinkedIn regex."""
        entities = []
        seen_names = set()

        # spaCy NER for organizations
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == "ORG":
                name = ent.text.strip()
                name_lower = name.lower()
                if name_lower not in seen_names and len(name) > 1:
                    seen_names.add(name_lower)
                    entities.append(ExtractedEntity(
                        text=name,
                        entity_type=EntityType.COMPANY,
                        start_pos=ent.start_char,
                        end_pos=ent.end_char,
                        confidence=0.8,
                    ))

        # URL-based company extraction
        for match in URL_PATTERN.finditer(text):
            url = match.group(0)
            domain = match.group(1)

            # Skip common non-company URLs
            skip_domains = {"linkedin.com", "google.com", "gmail.com", "github.com", "twitter.com", "x.com"}
            base_domain = ".".join(domain.split(".")[-2:])
            if base_domain in skip_domains:
                continue

            company_name = domain.split(".")[0].title()
            if company_name.lower() not in seen_names:
                seen_names.add(company_name.lower())
                entities.append(ExtractedEntity(
                    text=company_name,
                    entity_type=EntityType.COMPANY,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9,
                    metadata={"url": url},
                ))

        # LinkedIn company URLs
        for match in LINKEDIN_COMPANY_PATTERN.finditer(text):
            slug = match.group(1)
            name = slug.replace("-", " ").title()
            linkedin_url = f"https://www.linkedin.com/company/{slug}"
            if name.lower() not in seen_names:
                seen_names.add(name.lower())
                entities.append(ExtractedEntity(
                    text=name,
                    entity_type=EntityType.COMPANY,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95,
                    metadata={"linkedin_url": linkedin_url},
                ))

        return entities

    def extract_people(self, text: str) -> list[ExtractedEntity]:
        """Extract person mentions using spaCy PERSON + email/LinkedIn regex."""
        entities = []
        seen_names = set()

        # spaCy NER for people
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                name_lower = name.lower()
                if name_lower not in seen_names and len(name) > 1:
                    seen_names.add(name_lower)
                    entities.append(ExtractedEntity(
                        text=name,
                        entity_type=EntityType.PERSON,
                        start_pos=ent.start_char,
                        end_pos=ent.end_char,
                        confidence=0.8,
                    ))

        # Email-based person extraction
        for match in EMAIL_PATTERN.finditer(text):
            email = match.group(0)
            local_part = email.split("@")[0]
            # Try to extract name from email (e.g., john.doe -> John Doe)
            name_parts = re.split(r'[._]', local_part)
            name = " ".join(p.title() for p in name_parts if len(p) > 1)
            if name and name.lower() not in seen_names:
                seen_names.add(name.lower())
                entities.append(ExtractedEntity(
                    text=name,
                    entity_type=EntityType.PERSON,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.7,
                    metadata={"email": email},
                ))

        # LinkedIn person URLs
        for match in LINKEDIN_PERSON_PATTERN.finditer(text):
            slug = match.group(1)
            name = slug.replace("-", " ").title()
            linkedin_url = f"https://www.linkedin.com/in/{slug}"
            if name.lower() not in seen_names:
                seen_names.add(name.lower())
                entities.append(ExtractedEntity(
                    text=name,
                    entity_type=EntityType.PERSON,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95,
                    metadata={"linkedin_url": linkedin_url},
                ))

        return entities

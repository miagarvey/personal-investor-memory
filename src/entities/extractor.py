import json
import os
import re
from dataclasses import dataclass

from openai import AsyncOpenAI

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


# Regex patterns for structured data (URLs, emails, LinkedIn)
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

EXTRACTION_PROMPT = """\
Extract all company names and person names mentioned in the following text.
This text comes from a venture capital / investor context (memos, emails, meeting notes).

Rules:
- Companies: Extract actual company/startup names. Do NOT extract financial metrics \
(ARR, MRR, TAM), funding rounds (Series A), roles (CTO, CEO), or generic tech terms \
(SaaS, B2B, AI/ML, DevOps).
- People: Extract actual human names (first and last name). Do NOT extract roles, \
section headers, acronyms, or company names.
- Return each entity exactly once, using its canonical/clean name.
- If unsure whether something is an entity, omit it.

Return valid JSON with this exact structure:
{"companies": ["Company Name", ...], "people": ["First Last", ...]}

Text:
"""


class EntityExtractor:
    """
    Extracts entities (companies and people) from text.

    Uses OpenAI GPT-4o-mini for NER + regex for URLs/emails/LinkedIn.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model

    async def _extract_with_llm(self, text: str) -> tuple[list[str], list[str]]:
        """Call the LLM to extract company and person names from text."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You extract entities from investor/VC text. Respond only with valid JSON."},
                {"role": "user", "content": EXTRACTION_PROMPT + text},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return [], []

        companies = parsed.get("companies", [])
        people = parsed.get("people", [])

        # Ensure we got lists of strings
        if not isinstance(companies, list):
            companies = []
        if not isinstance(people, list):
            people = []

        return (
            [c for c in companies if isinstance(c, str) and c.strip()],
            [p for p in people if isinstance(p, str) and p.strip()],
        )

    async def extract(self, text: str) -> list[ExtractedEntity]:
        """Extract all entities (companies and people) from text."""
        # LLM-based extraction for unstructured text
        llm_companies, llm_people = await self._extract_with_llm(text)

        entities: list[ExtractedEntity] = []
        seen_names: set[str] = set()

        # Add LLM-extracted companies
        for name in llm_companies:
            name_lower = name.lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                # Find position in text if possible
                start = text.lower().find(name_lower)
                end = start + len(name) if start >= 0 else 0
                start = max(start, 0)
                entities.append(ExtractedEntity(
                    text=name,
                    entity_type=EntityType.COMPANY,
                    start_pos=start,
                    end_pos=end,
                    confidence=0.9,
                ))

        # Add LLM-extracted people
        for name in llm_people:
            name_lower = name.lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                start = text.lower().find(name_lower)
                end = start + len(name) if start >= 0 else 0
                start = max(start, 0)
                entities.append(ExtractedEntity(
                    text=name,
                    entity_type=EntityType.PERSON,
                    start_pos=start,
                    end_pos=end,
                    confidence=0.9,
                ))

        # Regex-based extraction for structured data (URLs, emails, LinkedIn)
        entities.extend(self._extract_from_urls(text, seen_names))
        entities.extend(self._extract_from_emails(text, seen_names))
        entities.extend(self._extract_from_linkedin(text, seen_names))

        return entities

    @staticmethod
    def _extract_from_urls(text: str, seen_names: set[str]) -> list[ExtractedEntity]:
        """Extract company entities from URLs."""
        entities = []
        skip_domains = {"linkedin.com", "google.com", "gmail.com", "github.com", "twitter.com", "x.com"}

        for match in URL_PATTERN.finditer(text):
            url = match.group(0)
            domain = match.group(1)
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
        return entities

    @staticmethod
    def _extract_from_emails(text: str, seen_names: set[str]) -> list[ExtractedEntity]:
        """Extract person entities from email addresses."""
        entities = []
        for match in EMAIL_PATTERN.finditer(text):
            email = match.group(0)
            local_part = email.split("@")[0]
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
        return entities

    @staticmethod
    def _extract_from_linkedin(text: str, seen_names: set[str]) -> list[ExtractedEntity]:
        """Extract entities from LinkedIn URLs."""
        entities = []

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

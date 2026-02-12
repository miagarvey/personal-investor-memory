"""Tests for entity extraction."""

from unittest.mock import AsyncMock, patch

import pytest

from src.entities.extractor import EntityExtractor, ExtractedEntity
from src.models import EntityType


@pytest.fixture
def entity_extractor():
    """Provide an entity extractor (does not require a real API key for mocked tests)."""
    return EntityExtractor(api_key="test-key")


def _mock_llm_response(companies: list[str], people: list[str]):
    """Create a mock OpenAI chat completion response."""
    import json
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content=json.dumps({
            "companies": companies,
            "people": people,
        })))
    ]
    return mock_response


@pytest.mark.asyncio
async def test_extract_companies_from_llm(entity_extractor):
    with patch.object(entity_extractor.client.chat.completions, "create",
                      new=AsyncMock(return_value=_mock_llm_response(["Google", "Microsoft"], []))):
        text = "We had a meeting with Google and Microsoft about their cloud offerings."
        entities = await entity_extractor.extract(text)
        companies = [e for e in entities if e.entity_type == EntityType.COMPANY]
        names = [e.text for e in companies]
        assert "Google" in names
        assert "Microsoft" in names


@pytest.mark.asyncio
async def test_extract_companies_from_url(entity_extractor):
    with patch.object(entity_extractor.client.chat.completions, "create",
                      new=AsyncMock(return_value=_mock_llm_response([], []))):
        text = "Check out https://novabuild.io for more information."
        entities = await entity_extractor.extract(text)
        assert len(entities) >= 1
        assert any(e.metadata and "url" in e.metadata for e in entities)


@pytest.mark.asyncio
async def test_extract_people_from_llm(entity_extractor):
    with patch.object(entity_extractor.client.chat.completions, "create",
                      new=AsyncMock(return_value=_mock_llm_response([], ["Sarah Chen", "Marcus Rivera"]))):
        text = "Sarah Chen presented the pitch deck. Marcus Rivera asked about unit economics."
        entities = await entity_extractor.extract(text)
        people = [e for e in entities if e.entity_type == EntityType.PERSON]
        names = [e.text for e in people]
        assert "Sarah Chen" in names
        assert "Marcus Rivera" in names


@pytest.mark.asyncio
async def test_extract_people_from_email(entity_extractor):
    with patch.object(entity_extractor.client.chat.completions, "create",
                      new=AsyncMock(return_value=_mock_llm_response([], []))):
        text = "Please contact john.doe@example.com for details."
        entities = await entity_extractor.extract(text)
        assert len(entities) >= 1
        assert any(e.metadata and e.metadata.get("email") == "john.doe@example.com" for e in entities)


@pytest.mark.asyncio
async def test_extract_all(entity_extractor):
    with patch.object(entity_extractor.client.chat.completions, "create",
                      new=AsyncMock(return_value=_mock_llm_response(["NovaBuild"], ["Sarah Chen"]))):
        text = "Sarah Chen from NovaBuild presented their platform."
        entities = await entity_extractor.extract(text)
        types = {e.entity_type for e in entities}
        assert EntityType.COMPANY in types
        assert EntityType.PERSON in types


@pytest.mark.asyncio
async def test_rejects_non_company_acronyms(entity_extractor):
    """The LLM should not return financial metrics as companies."""
    # Simulate what a well-prompted LLM should return: no false positives
    with patch.object(entity_extractor.client.chat.completions, "create",
                      new=AsyncMock(return_value=_mock_llm_response([], []))):
        text = (
            "The CTO walked us through the product. "
            "ARR grew from $2M to $3.5M. TAM is estimated at $5B. "
            "NPS of 70+."
        )
        entities = await entity_extractor.extract(text)
        company_names = [e.text.lower() for e in entities if e.entity_type == EntityType.COMPANY]
        for term in ["cto", "arr", "tam", "nps"]:
            assert term not in company_names, f"'{term}' should not be extracted as a company"


@pytest.mark.asyncio
async def test_deduplicates_llm_and_regex(entity_extractor):
    """LLM-extracted entity should not be duplicated by regex extraction."""
    with patch.object(entity_extractor.client.chat.completions, "create",
                      new=AsyncMock(return_value=_mock_llm_response(["Novabuild"], []))):
        text = "Check out NovaBuild at https://novabuild.io for details."
        entities = await entity_extractor.extract(text)
        company_names = [e.text.lower() for e in entities if e.entity_type == EntityType.COMPANY]
        assert company_names.count("novabuild") == 1


@pytest.mark.asyncio
async def test_linkedin_extraction(entity_extractor):
    with patch.object(entity_extractor.client.chat.completions, "create",
                      new=AsyncMock(return_value=_mock_llm_response([], []))):
        text = "See https://www.linkedin.com/company/stripe and https://www.linkedin.com/in/john-doe"
        entities = await entity_extractor.extract(text)

        companies = [e for e in entities if e.entity_type == EntityType.COMPANY]
        people = [e for e in entities if e.entity_type == EntityType.PERSON]

        assert any("Stripe" in e.text for e in companies)
        assert any("John Doe" in e.text for e in people)
        assert any(e.metadata and "linkedin_url" in e.metadata for e in companies)
        assert any(e.metadata and "linkedin_url" in e.metadata for e in people)

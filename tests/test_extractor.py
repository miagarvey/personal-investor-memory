"""Tests for entity extraction."""

import pytest

from src.models import EntityType


def test_extract_companies_from_spacy(entity_extractor):
    text = "We had a meeting with Google and Microsoft about their cloud offerings."
    companies = entity_extractor.extract_companies(text)
    names = [e.text for e in companies]
    assert any("Google" in n for n in names) or any("Microsoft" in n for n in names)
    for e in companies:
        assert e.entity_type == EntityType.COMPANY


def test_extract_companies_from_url(entity_extractor):
    text = "Check out https://novabuild.io for more information."
    companies = entity_extractor.extract_companies(text)
    assert len(companies) >= 1
    assert any(e.metadata and "url" in e.metadata for e in companies)


def test_extract_people_from_spacy(entity_extractor):
    text = "Sarah Chen presented the pitch deck. Marcus Rivera asked about unit economics."
    people = entity_extractor.extract_people(text)
    names = [e.text for e in people]
    assert any("Sarah Chen" in n for n in names)
    for e in people:
        assert e.entity_type == EntityType.PERSON


def test_extract_people_from_email(entity_extractor):
    text = "Please contact john.doe@example.com for details."
    people = entity_extractor.extract_people(text)
    assert len(people) >= 1
    assert any(e.metadata and e.metadata.get("email") == "john.doe@example.com" for e in people)


def test_extract_all(entity_extractor):
    text = "Sarah Chen from NovaBuild presented their platform."
    entities = entity_extractor.extract(text)
    types = {e.entity_type for e in entities}
    # Should find companies and/or people
    assert EntityType.COMPANY in types or EntityType.PERSON in types


def test_rejects_non_company_acronyms(entity_extractor):
    """CTO, ARR, TAM etc. should not be extracted as companies."""
    text = (
        "The CTO walked us through the product. "
        "ARR grew from $2M to $3.5M. TAM is estimated at $5B. "
        "NPS of 70+."
    )
    companies = entity_extractor.extract_companies(text)
    names = [e.text.lower() for e in companies]
    for term in ["cto", "arr", "tam", "nps"]:
        assert term not in names, f"'{term}' should not be extracted as a company"


def test_strips_trailing_noise_from_company_names(entity_extractor):
    """Company names with trailing context should be cleaned to the core name."""
    text = "Subject: Intro: Fivetran - data infrastructure\n\nWanted to flag Fivetran for the group."
    companies = entity_extractor.extract_companies(text)
    names = [e.text for e in companies]
    # Should not have "Fivetran - data infrastructure" as a separate entity
    for name in names:
        assert " - " not in name, f"Got noisy name: '{name}'"


def test_deduplicates_after_cleaning(entity_extractor):
    """'Fivetran - Follow-up' and 'Fivetran' should resolve to one entity."""
    text = (
        "Subject: Re: Fivetran - Follow-up thoughts\n\n"
        "Circling back on Fivetran after the deep-dive."
    )
    companies = entity_extractor.extract_companies(text)
    fivetran_matches = [e for e in companies if "fivetran" in e.text.lower()]
    assert len(fivetran_matches) <= 1, (
        f"Expected at most 1 Fivetran entity, got {len(fivetran_matches)}: "
        f"{[e.text for e in fivetran_matches]}"
    )


def test_clean_company_name_static():
    """Unit test the _clean_company_name helper directly."""
    from src.entities.extractor import EntityExtractor

    clean = EntityExtractor._clean_company_name
    assert clean("Fivetran - data infrastructure") == "Fivetran"
    assert clean("Fivetran Series A") == "Fivetran"
    assert clean("Fivetran Q4 Portfolio Update") == "Fivetran"
    assert clean("Fivetran - Follow-up thoughts") == "Fivetran"
    assert clean("ARR") is None
    assert clean("CTO") is None
    assert clean("Series A") is None
    assert clean("Google") == "Google"
    assert clean("Hugging Face") == "Hugging Face"

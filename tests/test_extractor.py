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

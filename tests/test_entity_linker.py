"""Tests for entity linking."""

import pytest

from src.models import EntityType
from src.entities.extractor import ExtractedEntity


@pytest.mark.asyncio
async def test_link_company_creates_new(entity_linker):
    company = await entity_linker.link_company(name="NewCorp")
    assert company.name == "NewCorp"
    assert company.id is not None


@pytest.mark.asyncio
async def test_link_company_deduplicates_by_name(entity_linker):
    c1 = await entity_linker.link_company(name="DedupCorp")
    c2 = await entity_linker.link_company(name="DedupCorp")
    assert c1.id == c2.id


@pytest.mark.asyncio
async def test_link_company_deduplicates_by_url(entity_linker):
    c1 = await entity_linker.link_company(name="UrlCorp", url="https://urlcorp.com")
    c2 = await entity_linker.link_company(name="URL Corp Different Name", url="https://urlcorp.com")
    assert c1.id == c2.id


@pytest.mark.asyncio
async def test_link_person_creates_new(entity_linker):
    person = await entity_linker.link_person(name="Jane Doe")
    assert person.name == "Jane Doe"


@pytest.mark.asyncio
async def test_link_person_deduplicates_by_email(entity_linker):
    p1 = await entity_linker.link_person(name="Jane", email="jane@example.com")
    p2 = await entity_linker.link_person(name="Jane D.", email="jane@example.com")
    assert p1.id == p2.id


@pytest.mark.asyncio
async def test_link_entity_dispatches_correctly(entity_linker):
    company_ext = ExtractedEntity(
        text="TestCo",
        entity_type=EntityType.COMPANY,
        start_pos=0,
        end_pos=6,
        metadata={"url": "https://testco.com"},
    )
    entity = await entity_linker.link_entity(company_ext)
    assert entity.entity_type == EntityType.COMPANY

    person_ext = ExtractedEntity(
        text="Alice",
        entity_type=EntityType.PERSON,
        start_pos=0,
        end_pos=5,
        metadata={"email": "alice@test.com"},
    )
    entity = await entity_linker.link_entity(person_ext)
    assert entity.entity_type == EntityType.PERSON

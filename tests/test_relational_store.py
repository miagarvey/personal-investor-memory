"""Tests for the relational storage layer."""

import pytest
from datetime import datetime

from src.models import Company, Person, Theme, Interaction, Artifact, Chunk, SourceType


@pytest.mark.asyncio
async def test_save_and_get_company(storage):
    company = Company(name="TestCorp", url="https://testcorp.com", description="A test company")
    await storage.save_company(company)

    retrieved = await storage.get_company(company.id)
    assert retrieved is not None
    assert retrieved.name == "TestCorp"
    assert retrieved.url == "https://testcorp.com"


@pytest.mark.asyncio
async def test_get_company_by_url(storage):
    company = Company(name="UrlCorp", url="https://urlcorp.io")
    await storage.save_company(company)

    found = await storage.get_company_by_url("https://urlcorp.io")
    assert found is not None
    assert found.id == company.id


@pytest.mark.asyncio
async def test_search_companies_by_name(storage):
    await storage.save_company(Company(name="NovaBuild"))
    await storage.save_company(Company(name="NovaWorks"))
    await storage.save_company(Company(name="OtherCo"))

    results = await storage.search_companies_by_name("Nova")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_save_and_get_person(storage):
    person = Person(name="Alice Smith", email="alice@example.com")
    await storage.save_person(person)

    retrieved = await storage.get_person(person.id)
    assert retrieved is not None
    assert retrieved.name == "Alice Smith"
    assert retrieved.email == "alice@example.com"


@pytest.mark.asyncio
async def test_get_person_by_email(storage):
    person = Person(name="Bob Jones", email="bob@example.com")
    await storage.save_person(person)

    found = await storage.get_person_by_email("bob@example.com")
    assert found is not None
    assert found.id == person.id


@pytest.mark.asyncio
async def test_save_and_get_theme(storage):
    theme = Theme(name="enterprise SaaS", keywords=["enterprise saas", "b2b saas"])
    await storage.save_theme(theme)

    retrieved = await storage.get_theme(theme.id)
    assert retrieved is not None
    assert retrieved.name == "enterprise SaaS"
    assert "enterprise saas" in retrieved.keywords


@pytest.mark.asyncio
async def test_get_theme_by_name(storage):
    theme = Theme(name="fintech", keywords=["fintech"])
    await storage.save_theme(theme)

    found = await storage.get_theme_by_name("fintech")
    assert found is not None
    assert found.id == theme.id


@pytest.mark.asyncio
async def test_save_and_get_interaction(storage):
    person = Person(name="Charlie Brown")
    await storage.save_person(person)

    interaction = Interaction(
        source_type=SourceType.EMAIL,
        raw_text="Hello world",
        timestamp=datetime.utcnow(),
        participants=[person.id],
    )
    await storage.save_interaction(interaction)

    retrieved = await storage.get_interaction(interaction.id)
    assert retrieved is not None
    assert retrieved.raw_text == "Hello world"
    assert person.id in retrieved.participants


@pytest.mark.asyncio
async def test_save_chunk_and_get_by_entity(storage):
    company = Company(name="ChunkCorp")
    await storage.save_company(company)

    chunk = Chunk(
        text="Some text about ChunkCorp",
        source_id=company.id,  # Using as source for simplicity
        source_type=SourceType.EMAIL,
        entity_ids=[company.id],
    )
    await storage.save_chunk(chunk)

    chunks = await storage.get_chunks_by_entity(company.id)
    assert len(chunks) == 1
    assert chunks[0].text == "Some text about ChunkCorp"


@pytest.mark.asyncio
async def test_get_chunks_by_source(storage):
    from uuid import uuid4
    source_id = uuid4()

    chunk1 = Chunk(text="First chunk", source_id=source_id, source_type=SourceType.DOCUMENT)
    chunk2 = Chunk(text="Second chunk", source_id=source_id, source_type=SourceType.DOCUMENT)
    await storage.save_chunk(chunk1)
    await storage.save_chunk(chunk2)

    chunks = await storage.get_chunks_by_source(source_id)
    assert len(chunks) == 2

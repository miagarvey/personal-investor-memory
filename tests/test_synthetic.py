"""Tests for the synthetic data generator."""

import pytest

from src.data.synthetic import SyntheticDataGenerator


def test_generate_all_produces_correct_count():
    gen = SyntheticDataGenerator()
    items = gen.generate_all()
    # 10 companies * 5 types = 50 items
    assert len(items) == 50


def test_generate_all_has_all_types():
    gen = SyntheticDataGenerator()
    items = gen.generate_all()
    types = {item["type"] for item in items}
    assert "email" in types
    assert "meeting" in types
    assert "document" in types


def test_generated_emails_have_required_fields():
    gen = SyntheticDataGenerator()
    items = gen.generate_all()
    emails = [i for i in items if i["type"] == "email"]
    for email in emails:
        assert "subject" in email
        assert "body" in email
        assert "sender" in email
        assert "recipients" in email
        assert "timestamp" in email


def test_generated_meetings_have_required_fields():
    gen = SyntheticDataGenerator()
    items = gen.generate_all()
    meetings = [i for i in items if i["type"] == "meeting"]
    for meeting in meetings:
        assert "title" in meeting
        assert "notes" in meeting
        assert "attendees" in meeting
        assert "timestamp" in meeting


@pytest.mark.asyncio
async def test_seed_database(pipeline):
    gen = SyntheticDataGenerator()
    count = await gen.seed_database(pipeline)
    assert count == 50

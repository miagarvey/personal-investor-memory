"""Synthetic data generator for seeding the investor memory system."""

import random
from datetime import datetime, timedelta

from src.ingestion.pipeline import IngestionPipeline
from src.models import SourceType


# === Real company pool (NEA AI/ML infrastructure portfolio) ===
COMPANIES = [
    {"name": "Anyscale", "domain": "AI/ML infrastructure", "desc": "distributed compute platform behind Ray for scalable ML training, serving, and RL"},
    {"name": "Databricks", "domain": "data infrastructure", "desc": "lakehouse architecture providing foundational data and ML platform for modern AI stacks"},
    {"name": "Weaviate", "domain": "AI/ML infrastructure", "desc": "open-source vector database for semantic search, RAG, and AI-native applications"},
    {"name": "Instabase", "domain": "AI/ML infrastructure", "desc": "unstructured data understanding platform bridging documents to machine-readable systems"},
    {"name": "Snorkel AI", "domain": "AI/ML infrastructure", "desc": "programmatic data labeling and supervision for building ML systems without hand-labeling"},
    {"name": "Hugging Face", "domain": "AI/ML infrastructure", "desc": "model hub and tooling layer for open ML with core distribution and collaboration infra"},
    {"name": "Domino Data Lab", "domain": "MLOps", "desc": "end-to-end MLOps platform for regulated and enterprise ML workloads"},
    {"name": "Cohere", "domain": "AI/ML infrastructure", "desc": "LLM provider focused on enterprise APIs and deployment flexibility"},
    {"name": "Scale AI", "domain": "AI/ML infrastructure", "desc": "data engine for training and evaluating frontier AI models"},
    {"name": "Fivetran", "domain": "data infrastructure", "desc": "automated data movement layer feeding analytics and ML systems"},
]

# === Real founders/CEOs ===
FOUNDERS = [
    {"name": "Robert Nishihara", "role": "CEO", "company": "Anyscale"},
    {"name": "Ali Ghodsi", "role": "CEO", "company": "Databricks"},
    {"name": "Bob van Luijt", "role": "CEO", "company": "Weaviate"},
    {"name": "Anant Bhardwaj", "role": "CEO", "company": "Instabase"},
    {"name": "Alex Ratner", "role": "CEO", "company": "Snorkel AI"},
    {"name": "Clément Delangue", "role": "CEO", "company": "Hugging Face"},
    {"name": "Nick Elprin", "role": "CEO", "company": "Domino Data Lab"},
    {"name": "Aidan Gomez", "role": "CEO", "company": "Cohere"},
    {"name": "Alexandr Wang", "role": "CEO", "company": "Scale AI"},
    {"name": "George Fraser", "role": "CEO", "company": "Fivetran"},
]

PARTNERS = [
    {"name": "Michael Torres", "role": "General Partner"},
    {"name": "Jessica Wu", "role": "Partner"},
    {"name": "David Nguyen", "role": "Principal"},
]


class SyntheticDataGenerator:
    """Generates synthetic VC-domain data for development and testing."""

    def _random_date(self, days_back: int = 90) -> datetime:
        return datetime.utcnow() - timedelta(days=random.randint(1, days_back))

    def generate_deal_intro_email(self, company: dict, founder: dict) -> dict:
        partner = random.choice(PARTNERS)
        return {
            "type": "email",
            "subject": f"Intro: {company['name']} - {company['domain']}",
            "body": (
                f"Hi team,\n\n"
                f"Wanted to flag {company['name']} for the group. {founder['name']} ({founder['role']}) "
                f"reached out through our network.\n\n"
                f"{company['name']} is building {company['desc']}. "
                f"They're at $2M ARR growing 3x YoY with strong {company['domain']} tailwinds. "
                f"The team is ex-Google/Stripe with deep domain expertise.\n\n"
                f"I think this is worth a first meeting. The {company['domain']} space is heating up "
                f"and their approach to the problem is differentiated.\n\n"
                f"Best,\n{partner['name']}"
            ),
            "sender": partner["name"],
            "recipients": ["team@fund.com"],
            "timestamp": self._random_date(),
        }

    def generate_deal_review_email(self, company: dict, founder: dict) -> dict:
        partner = random.choice(PARTNERS)
        themes = ["unit economics", "competitive moat", "go-to-market", "product-market fit", "TAM concerns"]
        selected = random.sample(themes, 2)
        return {
            "type": "email",
            "subject": f"Re: {company['name']} - Follow-up thoughts",
            "body": (
                f"Team,\n\n"
                f"Circling back on {company['name']} after the deep-dive with {founder['name']}.\n\n"
                f"Key observations:\n"
                f"- Strong {selected[0]} story: their gross margins are 80%+ and improving\n"
                f"- {selected[1].title()} is the main discussion point. {founder['name']} has a clear plan "
                f"but execution risk remains.\n"
                f"- Customer references were very positive. NPS of 70+.\n"
                f"- Burn rate is ~$200K/month with 18 months runway.\n\n"
                f"I'd recommend moving to partner vote. Thoughts?\n\n"
                f"{partner['name']}"
            ),
            "sender": partner["name"],
            "recipients": ["team@fund.com"],
            "timestamp": self._random_date(60),
        }

    def generate_portfolio_update(self, company: dict, founder: dict) -> dict:
        metrics = [
            f"ARR grew from $2M to $3.5M this quarter",
            f"Added 15 new enterprise customers",
            f"Net retention at 135%",
            f"Expanded engineering team to 20 people",
            f"Launched new product line targeting mid-market",
        ]
        selected = random.sample(metrics, 3)
        return {
            "type": "email",
            "subject": f"{company['name']} Q4 Portfolio Update",
            "body": (
                f"Hi all,\n\n"
                f"Quick update from {company['name']}:\n\n"
                f"- {selected[0]}\n"
                f"- {selected[1]}\n"
                f"- {selected[2]}\n\n"
                f"{founder['name']} is planning to raise a Series B in Q2. "
                f"They're targeting $20M at a $150M pre.\n\n"
                f"Overall the trajectory looks strong. The {company['domain']} thesis "
                f"is playing out well.\n\n"
                f"Best,\n{PARTNERS[0]['name']}"
            ),
            "sender": founder["name"],
            "recipients": [PARTNERS[0]["name"]],
            "timestamp": self._random_date(30),
        }

    def generate_pitch_meeting_notes(self, company: dict, founder: dict) -> dict:
        partner = random.choice(PARTNERS)
        return {
            "type": "meeting",
            "title": f"First Meeting: {company['name']} with {founder['name']}",
            "notes": (
                f"Meeting with {founder['name']} ({founder['role']}) of {company['name']}\n\n"
                f"## Company Overview\n"
                f"{company['name']} is building {company['desc']}.\n"
                f"Founded 2 years ago. Team of 12.\n\n"
                f"## Product\n"
                f"Their core product addresses a real pain point in {company['domain']}. "
                f"Enterprise SaaS model with land-and-expand motion. "
                f"Developer tools play a key role in their go-to-market strategy.\n\n"
                f"## Traction\n"
                f"- $2M ARR, growing 3x YoY\n"
                f"- 45 customers including 5 Fortune 500\n"
                f"- Net retention 130%+\n"
                f"- Product-market fit feels strong based on usage data\n\n"
                f"## Concerns\n"
                f"- TAM concerns: market may be smaller than presented. "
                f"Total addressable market estimate of $5B seems aggressive.\n"
                f"- Competitive moat unclear against larger incumbents\n"
                f"- Burn rate is manageable but unit economics need to improve at scale\n\n"
                f"## Next Steps\n"
                f"- Schedule deep-dive with CTO on technical architecture\n"
                f"- Customer reference calls\n"
                f"- {partner['name']} to lead diligence\n"
            ),
            "attendees": [partner["name"], founder["name"]],
            "timestamp": self._random_date(45),
        }

    def generate_deal_memo(self, company: dict, founder: dict) -> dict:
        return {
            "type": "document",
            "title": f"Deal Memo: {company['name']} Series A",
            "content": (
                f"# {company['name']} - Series A Investment Memo\n\n"
                f"## Executive Summary\n"
                f"{company['name']}, led by {founder['name']}, is building {company['desc']}. "
                f"The company has demonstrated strong product-market fit with $2M ARR growing 3x.\n\n"
                f"## Investment Thesis\n"
                f"1. Large and growing market in {company['domain']}\n"
                f"2. Exceptional founding team with deep domain expertise\n"
                f"3. Strong unit economics with 80%+ gross margins\n"
                f"4. Clear competitive moat through technology differentiation\n\n"
                f"## Key Risks\n"
                f"1. Execution risk on go-to-market expansion\n"
                f"2. TAM concerns if adjacent markets don't materialize\n"
                f"3. Competitive response from incumbents\n\n"
                f"## Financials\n"
                f"- Current ARR: $2M\n"
                f"- Burn rate: $200K/month\n"
                f"- Runway: 18 months\n"
                f"- Asking: $15M at $60M pre-money\n\n"
                f"## Recommendation\n"
                f"Proceed with $5M investment in the Series A round.\n"
            ),
            "timestamp": self._random_date(30),
        }

    def generate_all(self) -> list[dict]:
        """Generate a full set of synthetic data items."""
        items = []
        for i, company in enumerate(COMPANIES):
            founder = FOUNDERS[i]
            items.append(self.generate_deal_intro_email(company, founder))
            items.append(self.generate_deal_review_email(company, founder))
            items.append(self.generate_portfolio_update(company, founder))
            items.append(self.generate_pitch_meeting_notes(company, founder))
            items.append(self.generate_deal_memo(company, founder))
        return items

    async def seed_database(self, pipeline: IngestionPipeline) -> int:
        """Seed the database with synthetic data via the ingestion pipeline."""
        items = self.generate_all()
        count = 0

        for item in items:
            if item["type"] == "email":
                await pipeline.ingest_email(
                    subject=item["subject"],
                    body=item["body"],
                    sender=item["sender"],
                    recipients=item["recipients"],
                    timestamp=item["timestamp"],
                )
            elif item["type"] == "meeting":
                await pipeline.ingest_meeting_notes(
                    notes=item["notes"],
                    meeting_title=item["title"],
                    attendees=item["attendees"],
                    timestamp=item["timestamp"],
                )
            elif item["type"] == "document":
                await pipeline.ingest_artifact(
                    raw_text=item["content"],
                    source_type=SourceType.DOCUMENT,
                    title=item["title"],
                    timestamp=item["timestamp"],
                )
            count += 1

        return count

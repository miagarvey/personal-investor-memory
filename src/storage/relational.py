import json
from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.models import (
    Interaction, Artifact, Chunk,
    Company, Person, Theme, SourceType, EntityType
)
from src.storage.base import StorageBackend
from src.storage.models import (
    Base, CompanyRow, PersonRow, ThemeRow,
    InteractionRow, ArtifactRow, ChunkRow,
    interaction_participants, chunk_entities, artifact_companies,
)


class RelationalStore(StorageBackend):
    """
    Relational database storage using async SQLAlchemy.

    Uses sqlite+aiosqlite:/// for dev, postgresql+asyncpg:/// for production.
    """

    def __init__(self, connection_string: str = "sqlite+aiosqlite:///investor_memory.db"):
        self.connection_string = connection_string
        self.engine = create_async_engine(connection_string, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def initialize(self):
        """Create all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        await self.engine.dispose()

    def _session(self) -> AsyncSession:
        return self.session_factory()

    # === Conversions: domain model <-> ORM row ===

    @staticmethod
    def _company_from_row(row: CompanyRow) -> Company:
        return Company(
            id=UUID(row.id),
            name=row.name,
            url=row.url,
            linkedin_url=row.linkedin_url,
            description=row.description,
            created_at=row.created_at,
        )

    @staticmethod
    def _person_from_row(row: PersonRow) -> Person:
        return Person(
            id=UUID(row.id),
            name=row.name,
            linkedin_url=row.linkedin_url,
            email=row.email,
            company_id=UUID(row.company_id) if row.company_id else None,
            created_at=row.created_at,
        )

    @staticmethod
    def _theme_from_row(row: ThemeRow) -> Theme:
        return Theme(
            id=UUID(row.id),
            name=row.name,
            keywords=row.keywords,
            created_at=row.created_at,
        )

    @staticmethod
    def _interaction_from_row(row: InteractionRow, participant_ids: list[str] | None = None) -> Interaction:
        return Interaction(
            id=UUID(row.id),
            source_type=SourceType(row.source_type),
            raw_text=row.raw_text,
            timestamp=row.timestamp,
            participants=[UUID(pid) for pid in (participant_ids or [])],
            metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            created_at=row.created_at,
        )

    @staticmethod
    def _artifact_from_row(row: ArtifactRow) -> Artifact:
        return Artifact(
            id=UUID(row.id),
            source_type=SourceType(row.source_type),
            raw_text=row.raw_text,
            title=row.title,
            timestamp=row.timestamp,
            metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            created_at=row.created_at,
        )

    @staticmethod
    def _chunk_from_row(row: ChunkRow, entity_ids: list[str] | None = None) -> Chunk:
        return Chunk(
            id=UUID(row.id),
            text=row.text,
            source_id=UUID(row.source_id),
            source_type=SourceType(row.source_type),
            entity_ids=[UUID(eid) for eid in (entity_ids or [])],
            metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            created_at=row.created_at,
        )

    # === Interactions ===

    async def save_interaction(self, interaction: Interaction) -> None:
        async with self._session() as session:
            row = InteractionRow(
                id=str(interaction.id),
                source_type=interaction.source_type.value,
                raw_text=interaction.raw_text,
                timestamp=interaction.timestamp,
                metadata_json=json.dumps(interaction.metadata),
                created_at=interaction.created_at,
            )
            session.add(row)
            # Add participant associations
            for pid in interaction.participants:
                await session.execute(
                    interaction_participants.insert().values(
                        interaction_id=str(interaction.id),
                        person_id=str(pid),
                    )
                )
            await session.commit()

    async def get_interaction(self, id: UUID) -> Optional[Interaction]:
        async with self._session() as session:
            row = await session.get(InteractionRow, str(id))
            if not row:
                return None
            # Get participants
            result = await session.execute(
                select(interaction_participants.c.person_id).where(
                    interaction_participants.c.interaction_id == str(id)
                )
            )
            pids = [r[0] for r in result.fetchall()]
            return self._interaction_from_row(row, pids)

    async def get_interactions_by_participant(
        self, person_id: UUID, limit: int = 50
    ) -> list[Interaction]:
        async with self._session() as session:
            result = await session.execute(
                select(interaction_participants.c.interaction_id).where(
                    interaction_participants.c.person_id == str(person_id)
                )
            )
            iids = [r[0] for r in result.fetchall()]
            interactions = []
            for iid in iids[:limit]:
                row = await session.get(InteractionRow, iid)
                if row:
                    interactions.append(self._interaction_from_row(row))
            return interactions

    # === Artifacts ===

    async def save_artifact(self, artifact: Artifact) -> None:
        async with self._session() as session:
            row = ArtifactRow(
                id=str(artifact.id),
                source_type=artifact.source_type.value,
                raw_text=artifact.raw_text,
                title=artifact.title,
                timestamp=artifact.timestamp,
                metadata_json=json.dumps(artifact.metadata),
                created_at=artifact.created_at,
            )
            session.add(row)
            for cid in artifact.related_companies:
                await session.execute(
                    artifact_companies.insert().values(
                        artifact_id=str(artifact.id),
                        company_id=str(cid),
                    )
                )
            await session.commit()

    async def get_artifact(self, id: UUID) -> Optional[Artifact]:
        async with self._session() as session:
            row = await session.get(ArtifactRow, str(id))
            if not row:
                return None
            return self._artifact_from_row(row)

    # === Chunks ===

    async def save_chunk(self, chunk: Chunk) -> None:
        async with self._session() as session:
            row = ChunkRow(
                id=str(chunk.id),
                text=chunk.text,
                source_id=str(chunk.source_id),
                source_type=chunk.source_type.value,
                metadata_json=json.dumps(chunk.metadata),
                created_at=chunk.created_at,
            )
            session.add(row)
            # Save chunk-entity associations
            for eid in chunk.entity_ids:
                await session.execute(
                    chunk_entities.insert().values(
                        chunk_id=str(chunk.id),
                        entity_id=str(eid),
                        entity_type="",  # We don't always know the type here
                    )
                )
            await session.commit()

    async def get_chunks_by_source(self, source_id: UUID) -> list[Chunk]:
        async with self._session() as session:
            result = await session.execute(
                select(ChunkRow).where(ChunkRow.source_id == str(source_id))
            )
            rows = result.scalars().all()
            chunks = []
            for row in rows:
                eids = await self._get_chunk_entity_ids(session, row.id)
                chunks.append(self._chunk_from_row(row, eids))
            return chunks

    async def get_chunks_by_entity(self, entity_id: UUID, limit: int = 50) -> list[Chunk]:
        async with self._session() as session:
            result = await session.execute(
                select(chunk_entities.c.chunk_id).where(
                    chunk_entities.c.entity_id == str(entity_id)
                )
            )
            cids = [r[0] for r in result.fetchall()]
            chunks = []
            for cid in cids[:limit]:
                row = await session.get(ChunkRow, cid)
                if row:
                    eids = await self._get_chunk_entity_ids(session, row.id)
                    chunks.append(self._chunk_from_row(row, eids))
            return chunks

    async def _get_chunk_entity_ids(self, session: AsyncSession, chunk_id: str) -> list[str]:
        result = await session.execute(
            select(chunk_entities.c.entity_id).where(
                chunk_entities.c.chunk_id == chunk_id
            )
        )
        return [r[0] for r in result.fetchall()]

    # === Companies ===

    async def save_company(self, company: Company) -> None:
        async with self._session() as session:
            row = CompanyRow(
                id=str(company.id),
                name=company.name,
                url=company.url,
                linkedin_url=company.linkedin_url,
                description=company.description,
                created_at=company.created_at,
            )
            session.add(row)
            await session.commit()

    async def get_company(self, id: UUID) -> Optional[Company]:
        async with self._session() as session:
            row = await session.get(CompanyRow, str(id))
            return self._company_from_row(row) if row else None

    async def get_company_by_url(self, url: str) -> Optional[Company]:
        async with self._session() as session:
            result = await session.execute(
                select(CompanyRow).where(CompanyRow.url == url)
            )
            row = result.scalar_one_or_none()
            return self._company_from_row(row) if row else None

    async def get_company_by_linkedin(self, linkedin_url: str) -> Optional[Company]:
        async with self._session() as session:
            result = await session.execute(
                select(CompanyRow).where(CompanyRow.linkedin_url == linkedin_url)
            )
            row = result.scalar_one_or_none()
            return self._company_from_row(row) if row else None

    async def search_companies_by_name(
        self, name: str, limit: int = 5
    ) -> list[Company]:
        async with self._session() as session:
            result = await session.execute(
                select(CompanyRow)
                .where(CompanyRow.name.ilike(f"%{name}%"))
                .limit(limit)
            )
            return [self._company_from_row(r) for r in result.scalars().all()]

    # === People ===

    async def save_person(self, person: Person) -> None:
        async with self._session() as session:
            row = PersonRow(
                id=str(person.id),
                name=person.name,
                linkedin_url=person.linkedin_url,
                email=person.email,
                company_id=str(person.company_id) if person.company_id else None,
                created_at=person.created_at,
            )
            session.add(row)
            await session.commit()

    async def get_person(self, id: UUID) -> Optional[Person]:
        async with self._session() as session:
            row = await session.get(PersonRow, str(id))
            return self._person_from_row(row) if row else None

    async def get_person_by_email(self, email: str) -> Optional[Person]:
        async with self._session() as session:
            result = await session.execute(
                select(PersonRow).where(PersonRow.email == email)
            )
            row = result.scalar_one_or_none()
            return self._person_from_row(row) if row else None

    async def get_person_by_linkedin(self, linkedin_url: str) -> Optional[Person]:
        async with self._session() as session:
            result = await session.execute(
                select(PersonRow).where(PersonRow.linkedin_url == linkedin_url)
            )
            row = result.scalar_one_or_none()
            return self._person_from_row(row) if row else None

    async def search_people_by_name(
        self, name: str, limit: int = 5
    ) -> list[Person]:
        async with self._session() as session:
            result = await session.execute(
                select(PersonRow)
                .where(PersonRow.name.ilike(f"%{name}%"))
                .limit(limit)
            )
            return [self._person_from_row(r) for r in result.scalars().all()]

    # === Themes ===

    async def save_theme(self, theme: Theme) -> None:
        async with self._session() as session:
            row = ThemeRow(
                id=str(theme.id),
                name=theme.name,
                created_at=theme.created_at,
            )
            row.keywords = theme.keywords
            session.add(row)
            await session.commit()

    async def get_theme(self, id: UUID) -> Optional[Theme]:
        async with self._session() as session:
            row = await session.get(ThemeRow, str(id))
            return self._theme_from_row(row) if row else None

    async def get_theme_by_name(self, name: str) -> Optional[Theme]:
        async with self._session() as session:
            result = await session.execute(
                select(ThemeRow).where(ThemeRow.name == name)
            )
            row = result.scalar_one_or_none()
            return self._theme_from_row(row) if row else None

from datetime import datetime
from typing import Optional
from uuid import UUID

from src.models import Interaction, Artifact, Chunk, SourceType
from src.ingestion.chunker import TextChunker
from src.entities.extractor import EntityExtractor
from src.entities.linker import EntityLinker
from src.storage.base import StorageBackend
from src.storage.vector import VectorStore
from src.embeddings import EmbeddingService


class IngestionPipeline:
    """
    Main ingestion pipeline for Phase 1.

    Handles: emails, meeting notes, documents, newsletters.
    Steps:
      1. Parse raw input with metadata
      2. Chunk text
      3. Extract and link entities
      4. Embed chunks
      5. Store in vector + relational DB
    """

    def __init__(
        self,
        storage: StorageBackend,
        entity_extractor: EntityExtractor,
        entity_linker: EntityLinker,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        chunker: Optional[TextChunker] = None,
    ):
        self.storage = storage
        self.entity_extractor = entity_extractor
        self.entity_linker = entity_linker
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.chunker = chunker or TextChunker()

    async def ingest_interaction(
        self,
        raw_text: str,
        source_type: SourceType,
        timestamp: datetime,
        participants: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Interaction:
        """Ingest an interaction (email, meeting notes, etc.)."""
        # 1. Resolve participant names to Person entities
        participant_ids = []
        if participants:
            for name in participants:
                person = await self.entity_linker.link_person(name=name)
                participant_ids.append(person.id)

        # 2. Create Interaction object
        interaction = Interaction(
            source_type=source_type,
            raw_text=raw_text,
            timestamp=timestamp,
            participants=participant_ids,
            metadata=metadata or {},
        )
        await self.storage.save_interaction(interaction)

        # 3. Chunk the text
        chunk_texts = self.chunker.chunk_text(raw_text)

        # 4. Extract entities from each chunk, link, embed, and store
        all_chunk_texts = chunk_texts
        embeddings = await self.embedding_service.embed_batch(all_chunk_texts)

        for i, chunk_text in enumerate(all_chunk_texts):
            # Extract entities from this chunk
            extracted = self.entity_extractor.extract(chunk_text)

            # Link extracted entities to canonical entities
            entity_ids = []
            for ext in extracted:
                linked = await self.entity_linker.link_entity(ext)
                if linked.id not in entity_ids:
                    entity_ids.append(linked.id)

            # Create chunk
            chunk = Chunk(
                text=chunk_text,
                source_id=interaction.id,
                source_type=source_type,
                entity_ids=entity_ids,
                embedding=embeddings[i],
                metadata=metadata or {},
            )

            # 5. Store in relational DB and vector store
            await self.storage.save_chunk(chunk)
            await self.vector_store.upsert(chunk)

        return interaction

    async def ingest_artifact(
        self,
        raw_text: str,
        source_type: SourceType,
        title: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> Artifact:
        """Ingest an artifact (document, deck, etc.)."""
        artifact = Artifact(
            source_type=source_type,
            raw_text=raw_text,
            title=title,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata or {},
        )
        await self.storage.save_artifact(artifact)

        # Chunk, extract, embed, store
        chunk_texts = self.chunker.chunk_text(raw_text)
        embeddings = await self.embedding_service.embed_batch(chunk_texts)

        for i, chunk_text in enumerate(chunk_texts):
            extracted = self.entity_extractor.extract(chunk_text)
            entity_ids = []
            for ext in extracted:
                linked = await self.entity_linker.link_entity(ext)
                if linked.id not in entity_ids:
                    entity_ids.append(linked.id)

            chunk = Chunk(
                text=chunk_text,
                source_id=artifact.id,
                source_type=source_type,
                entity_ids=entity_ids,
                embedding=embeddings[i],
                metadata=metadata or {},
            )
            await self.storage.save_chunk(chunk)
            await self.vector_store.upsert(chunk)

        return artifact

    async def ingest_email(
        self,
        subject: str,
        body: str,
        sender: str,
        recipients: list[str],
        timestamp: datetime,
        thread_id: Optional[str] = None,
    ) -> Interaction:
        """Convenience method for email ingestion."""
        metadata = {
            "subject": subject,
            "sender": sender,
            "recipients": recipients,
            "thread_id": thread_id,
        }
        return await self.ingest_interaction(
            raw_text=f"Subject: {subject}\n\n{body}",
            source_type=SourceType.EMAIL,
            timestamp=timestamp,
            participants=[sender] + recipients,
            metadata=metadata,
        )

    async def ingest_meeting_notes(
        self,
        notes: str,
        meeting_title: str,
        attendees: list[str],
        timestamp: datetime,
    ) -> Interaction:
        """Convenience method for meeting notes ingestion."""
        metadata = {"meeting_title": meeting_title}
        return await self.ingest_interaction(
            raw_text=notes,
            source_type=SourceType.MEETING_NOTES,
            timestamp=timestamp,
            participants=attendees,
            metadata=metadata,
        )

from datetime import datetime
from typing import Optional
from uuid import UUID

from src.models import Interaction, Artifact, Chunk, SourceType
from src.ingestion.chunker import TextChunker
from src.entities.extractor import EntityExtractor
from src.storage.base import StorageBackend


class IngestionPipeline:
    """
    Main ingestion pipeline for Phase 1.

    Handles: emails, meeting notes, documents, newsletters.
    Steps:
      1. Parse raw input with metadata
      2. Chunk text
      3. Extract and link entities
      4. Store in vector + relational DB
    """

    def __init__(
        self,
        storage: StorageBackend,
        entity_extractor: EntityExtractor,
        chunker: Optional[TextChunker] = None,
    ):
        self.storage = storage
        self.entity_extractor = entity_extractor
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
        # TODO: Implement
        # 1. Create Interaction object
        # 2. Resolve participant names to Person entities
        # 3. Chunk the text
        # 4. Extract entities from each chunk
        # 5. Store interaction and chunks
        raise NotImplementedError

    async def ingest_artifact(
        self,
        raw_text: str,
        source_type: SourceType,
        title: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> Artifact:
        """Ingest an artifact (document, deck, etc.)."""
        # TODO: Implement
        raise NotImplementedError

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

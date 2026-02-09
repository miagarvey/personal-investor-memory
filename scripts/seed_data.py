#!/usr/bin/env python3
"""CLI script to seed the database with synthetic data."""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.relational import RelationalStore
from src.storage.vector import VectorStore, VectorStoreConfig
from src.embeddings import EmbeddingService
from src.entities.extractor import EntityExtractor
from src.entities.linker import EntityLinker
from src.ingestion.pipeline import IngestionPipeline
from src.data.synthetic import SyntheticDataGenerator


async def main():
    print("Initializing components...")

    storage = RelationalStore("sqlite+aiosqlite:///investor_memory.db")
    await storage.initialize()

    vector_store = VectorStore(VectorStoreConfig(embedding_dimension=384))
    embedding_service = EmbeddingService(backend="local")
    extractor = EntityExtractor()
    linker = EntityLinker(storage)

    pipeline = IngestionPipeline(
        storage=storage,
        entity_extractor=extractor,
        entity_linker=linker,
        vector_store=vector_store,
        embedding_service=embedding_service,
    )

    print("Generating and seeding synthetic data...")
    generator = SyntheticDataGenerator()
    count = await generator.seed_database(pipeline)
    print(f"Seeded {count} items into the database.")

    await storage.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())

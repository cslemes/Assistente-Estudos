"""
One-time script to create payload indexes on the Qdrant collection.
Required for filtering by course, topic, and aula_number in /flashcards and /classes.

Run: uv run python scripts/create_payload_indexes.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.http.models import PayloadSchemaType

from app.config.settings import Settings

settings = Settings()
client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

indexes = [
    ("course", PayloadSchemaType.KEYWORD),
    ("topic", PayloadSchemaType.KEYWORD),
    ("source_type", PayloadSchemaType.KEYWORD),
    ("aula_number", PayloadSchemaType.INTEGER),
]

for field, schema_type in indexes:
    print(f"Creating index: {field} ({schema_type}) ... ", end="", flush=True)
    client.create_payload_index(
        collection_name=settings.collection_name,
        field_name=field,
        field_schema=schema_type,
    )
    print("done")

print("\nAll indexes created.")

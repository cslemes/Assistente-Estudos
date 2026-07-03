"""
Update video_url in every Qdrant chunk payload by rebuilding it from:
  - The base YouTube URL stored in SQLite (after sync_video_urls.py has run)
  - The start_time already stored in each Qdrant point

Matches points to the correct video via (course, topic, aula_number).

Usage:
    python scripts/sync_qdrant_urls.py [--dry-run] [--collection aulas]
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import Settings
from app.database import get_connection
from app.services.ingestion import _get_qdrant_client, _extract_class_meta


def build_lookup() -> dict[tuple, str]:
    """Return {(course, topic, aula_number): base_video_url} from SQLite."""
    lookup: dict[tuple, str] = {}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT file_path, video_url FROM transcriptions WHERE video_url IS NOT NULL"
        ).fetchall()
    for row in rows:
        meta = _extract_class_meta(row["file_path"])
        key = (meta["course"], meta["topic"], meta["aula_number"])
        base = row["video_url"].split("?")[0]  # strip existing ?t=
        lookup[key] = base
    return lookup


def main():
    parser = argparse.ArgumentParser(description="Sync video_url in Qdrant from SQLite.")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing to Qdrant")
    parser.add_argument("--collection", default=None, help="Qdrant collection name (default: $COLLECTION_NAME or 'aulas')")
    args = parser.parse_args()

    settings = Settings()
    collection = args.collection or os.getenv("COLLECTION_NAME", "aulas")

    lookup = build_lookup()
    if not lookup:
        print("No video URLs found in SQLite. Run sync_video_urls.py first.")
        return
    print(f"Loaded {len(lookup)} URL mapping(s) from SQLite.")

    client = _get_qdrant_client()

    updated = 0
    skipped_no_match = 0
    skipped_no_time = 0
    offset = None

    while True:
        result = client.scroll(
            collection_name=collection,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = result

        if not points:
            break

        for point in points:
            payload = point.payload or {}
            course = payload.get("course")
            topic = payload.get("topic")
            aula_number = payload.get("aula_number")
            start_time = payload.get("start_time")

            key = (course, topic, aula_number)
            base_url = lookup.get(key)

            if not base_url:
                skipped_no_match += 1
                continue

            if start_time is None:
                new_url = base_url
            else:
                new_url = f"{base_url}?t={int(start_time)}"

            if args.dry_run:
                print(f"  [dry-run] id={point.id}  {key}  t={start_time}  →  {new_url}")
            else:
                client.set_payload(
                    collection_name=collection,
                    payload={"video_url": new_url},
                    points=[point.id],
                )
            updated += 1

        if next_offset is None:
            break
        offset = next_offset

    if args.dry_run:
        print(f"\n[dry-run] Would update {updated} point(s), {skipped_no_match} with no SQLite match.")
    else:
        print(f"\nDone: {updated} point(s) updated, {skipped_no_match} with no SQLite match.")


if __name__ == "__main__":
    main()

"""
Scan all .uploaded marker files in Downloads/ and update the video_url field
in the DB for any matching transcription records.

Usage:
    python scripts/sync_video_urls.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import set_video_url_by_stem

DOWNLOADS = Path(__file__).resolve().parent.parent / "Downloads"


def main():
    parser = argparse.ArgumentParser(description="Sync YouTube video URLs from .uploaded markers into the DB.")
    parser.add_argument("--dry-run", action="store_true", help="Print matches without updating the DB")
    args = parser.parse_args()

    markers = list(DOWNLOADS.rglob("*.uploaded"))
    if not markers:
        print("No .uploaded marker files found under Downloads/")
        return

    print(f"Found {len(markers)} marker file(s)\n")

    updated_total = 0
    unmatched = []

    for marker in sorted(markers):
        video_id = marker.read_text(encoding="utf-8").strip()
        if not video_id:
            print(f"  SKIP (empty) {marker.name}")
            continue

        # Marker name: Aula_01_Topic.mp4.uploaded → stem: Aula_01_Topic
        video_stem = marker.name
        for ext in (".mp4.uploaded", ".mkv.uploaded", ".mov.uploaded", ".webm.uploaded"):
            if video_stem.endswith(ext):
                video_stem = video_stem[: -len(ext)]
                break
        else:
            video_stem = Path(video_stem).stem  # fallback

        video_url = f"https://youtu.be/{video_id}"

        if args.dry_run:
            print(f"  [dry-run] stem={video_stem!r}  url={video_url}")
            continue

        rows = set_video_url_by_stem(video_stem, video_url)
        if rows:
            print(f"  ✓ {video_stem}  →  {video_url}  ({rows} row(s) updated)")
            updated_total += rows
        else:
            unmatched.append(video_stem)
            print(f"  ✗ {video_stem}  →  no DB match")

    if not args.dry_run:
        print(f"\nDone: {updated_total} DB row(s) updated, {len(unmatched)} unmatched marker(s).")
        if unmatched:
            print("\nUnmatched stems (no transcription in DB yet):")
            for s in unmatched:
                print(f"  - {s}")


if __name__ == "__main__":
    main()

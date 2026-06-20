"""
Upload all video files from the Downloads folder to S3-compatible object storage.

Skips files that already have a .storage marker (previously uploaded).
After each successful upload, updates the video_url in SQLite so the frontend
can stream the video directly from storage.

Usage:
    python scripts/upload_videos.py                    # dry-run
    python scripts/upload_videos.py --apply            # upload
    python scripts/upload_videos.py --apply --force    # re-upload even if already uploaded
    python scripts/upload_videos.py --apply --folder "Downloads/PLNA 2025.2"
"""

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.config.settings import Settings, VIDEO_EXTENSIONS
from app.database import set_video_url_by_stem
import app.services.storage as storage_svc

DOWNLOADS_DIR = Path(__file__).resolve().parent.parent / "Downloads"
MARKER_SUFFIX = ".storage"


def find_videos(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*")
        if p.suffix.lower() in VIDEO_EXTENSIONS
    )


def format_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="Execute uploads (default: dry-run)")
    parser.add_argument("--force", action="store_true", help="Re-upload even if .storage marker exists")
    parser.add_argument("--folder", type=Path, default=DOWNLOADS_DIR, help="Root folder to scan (default: Downloads/)")
    args = parser.parse_args()

    s = Settings()

    print("=== Object Storage Upload ===")
    print(f"  Endpoint : {s.storage_endpoint_url or 'AWS S3 (default region)'}")
    print(f"  Bucket   : {s.storage_bucket_name}")
    print(f"  Public   : {s.storage_public_url}")
    print(f"  Mode     : {'APPLY' if args.apply else 'DRY-RUN'}")
    print()

    if not storage_svc.is_configured():
        print("ERROR: Object storage not configured.")
        print("  Set STORAGE_ACCESS_KEY_ID and STORAGE_SECRET_ACCESS_KEY in .env")
        sys.exit(1)

    all_videos = find_videos(args.folder)
    if not all_videos:
        print(f"No video files found under {args.folder}")
        return

    # Split into pending and already-uploaded
    pending, already = [], []
    for v in all_videos:
        if not args.force and (v.parent / (v.name + MARKER_SUFFIX)).exists():
            already.append(v)
        else:
            pending.append(v)

    print(f"Found {len(all_videos)} video(s): {len(pending)} to upload, {len(already)} already done.")
    if not pending:
        print("Nothing to upload.")
        return

    print()

    total_bytes = sum(v.stat().st_size for v in pending)
    uploaded_bytes = 0
    ok = 0
    failed = 0

    for i, video in enumerate(pending, 1):
        key = storage_svc.video_key(str(video))
        size = video.stat().st_size
        prefix = f"[{i}/{len(pending)}]"

        print(f"{prefix} {video.name}")
        print(f"         {format_size(size)}  →  {key}")

        if not args.apply:
            print(f"         [dry-run] skipped")
            continue

        t0 = time.monotonic()
        url = storage_svc.upload_file(str(video), key)
        elapsed = time.monotonic() - t0

        if url:
            marker = video.parent / (video.name + MARKER_SUFFIX)
            marker.write_text(url, encoding="utf-8")

            stem = video.stem
            rows = set_video_url_by_stem(stem, url)

            uploaded_bytes += size
            ok += 1
            speed = size / elapsed / (1024 * 1024) if elapsed > 0 else 0
            print(f"         OK  {elapsed:.1f}s  {speed:.1f} MB/s  db_rows={rows}")
            print(f"         URL: {url}")
        else:
            failed += 1
            print(f"         FAILED — check logs for details")

        print()

    if args.apply:
        print(f"Done: {ok} uploaded ({format_size(uploaded_bytes)}), {failed} failed, {len(already)} already done.")
    else:
        total_mb = total_bytes / (1024 * 1024)
        print(f"[dry-run] Would upload {len(pending)} file(s) ({total_mb:.1f} MB). Run with --apply to proceed.")


if __name__ == "__main__":
    main()

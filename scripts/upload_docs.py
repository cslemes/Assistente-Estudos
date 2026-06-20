"""
Upload lesson documents and scripts to S3-compatible object storage.

Scans every lesson folder under Downloads/ for documentos/ and scripts/ subdirectories
and uploads all files found there. Skips files that already have a .storage marker.
After each successful upload writes a .storage marker file containing the public URL.

Usage:
    python scripts/upload_docs.py                    # dry-run
    python scripts/upload_docs.py --apply            # upload
    python scripts/upload_docs.py --apply --force    # re-upload even if .storage exists
    python scripts/upload_docs.py --apply --folder "Downloads/PLNA 2025.2"
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.config.settings import Settings
import app.services.storage as storage_svc

DOWNLOADS_DIR = Path(__file__).resolve().parent.parent / "Downloads"
MARKER_SUFFIX = ".storage"
SCAN_SUBDIRS  = ("documentos", "scripts")


def find_docs(root: Path) -> list[Path]:
    files = []
    for subdir in SCAN_SUBDIRS:
        files.extend(root.rglob(f"{subdir}/*"))
    return sorted(f for f in files if f.is_file() and not f.name.endswith(MARKER_SUFFIX))


def format_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply",  action="store_true", help="Execute uploads (default: dry-run)")
    parser.add_argument("--force",  action="store_true", help="Re-upload even if .storage marker exists")
    parser.add_argument("--folder", type=Path, default=DOWNLOADS_DIR, help="Root folder to scan")
    args = parser.parse_args()

    s = Settings()
    print("=== Docs Storage Upload ===")
    print(f"  Endpoint : {s.storage_endpoint_url or 'AWS S3 (default region)'}")
    print(f"  Bucket   : {s.storage_bucket_name}")
    print(f"  Public   : {s.storage_public_url}")
    print(f"  Mode     : {'APPLY' if args.apply else 'DRY-RUN'}")
    print()

    if not storage_svc.is_configured():
        print("ERROR: Object storage not configured.")
        print("  Set STORAGE_ACCESS_KEY_ID and STORAGE_SECRET_ACCESS_KEY in .env")
        sys.exit(1)

    all_docs = find_docs(args.folder)
    if not all_docs:
        print(f"No documents found under {args.folder}")
        return

    pending, already = [], []
    for f in all_docs:
        if not args.force and (f.parent / (f.name + MARKER_SUFFIX)).exists():
            already.append(f)
        else:
            pending.append(f)

    print(f"Found {len(all_docs)} file(s): {len(pending)} to upload, {len(already)} already done.")
    if not pending:
        print("Nothing to upload.")
        return
    print()

    ok = failed = 0
    uploaded_bytes = 0

    for i, doc in enumerate(pending, 1):
        key  = storage_svc.doc_key(str(doc))
        size = doc.stat().st_size
        print(f"[{i}/{len(pending)}] {doc.name}")
        print(f"         {format_size(size)}  →  {key}")

        if not args.apply:
            print("         [dry-run] skipped")
            continue

        t0  = time.monotonic()
        url = storage_svc.upload_file(str(doc), key)
        elapsed = time.monotonic() - t0

        if url:
            marker = doc.parent / (doc.name + MARKER_SUFFIX)
            marker.write_text(url, encoding="utf-8")
            uploaded_bytes += size
            ok += 1
            speed = size / elapsed / (1024 * 1024) if elapsed > 0 else 0
            print(f"         OK  {elapsed:.1f}s  {speed:.2f} MB/s")
            print(f"         URL: {url}")
        else:
            failed += 1
            print("         FAILED — check logs for details")
        print()

    if args.apply:
        print(f"Done: {ok} uploaded ({format_size(uploaded_bytes)}), {failed} failed, {len(already)} already done.")
    else:
        total_mb = sum(f.stat().st_size for f in pending) / (1024 * 1024)
        print(f"[dry-run] Would upload {len(pending)} file(s) ({total_mb:.1f} MB). Run with --apply to proceed.")


if __name__ == "__main__":
    main()

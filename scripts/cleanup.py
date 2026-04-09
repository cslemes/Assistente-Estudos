"""
Clean up transcription output files and reset DB records so the pipeline can be re-run.

Deletes .txt and .json files from ai_data/ folders and resets the corresponding
SQLite records (either to pending or fully deleted).

Usage:
    python scripts/cleanup.py /path/to/folder              # reset DB to pending
    python scripts/cleanup.py /path/to/folder --delete-db  # wipe DB records
    python scripts/cleanup.py /path/to/folder --recursive  # scan subfolders
    python scripts/cleanup.py /path/to/folder --dry-run    # preview only
"""

import argparse
import os
import sqlite3
from pathlib import Path

DB_PATH = os.path.join(os.getcwd(), "assistente.db")
CLEANUP_EXTENSIONS = (".txt", ".json")


def find_ai_data_files(folder: Path, recursive: bool) -> list[Path]:
    files = []
    if recursive:
        for ai_data in folder.rglob("ai_data"):
            if ai_data.is_dir():
                files.extend(
                    p for p in ai_data.iterdir()
                    if p.suffix.lower() in CLEANUP_EXTENSIONS
                )
    else:
        ai_data = folder / "ai_data"
        if ai_data.is_dir():
            files.extend(
                p for p in ai_data.iterdir()
                if p.suffix.lower() in CLEANUP_EXTENSIONS
            )
    return sorted(files)


def reset_db_record(conn: sqlite3.Connection, audio_path: str, delete: bool):
    if delete:
        conn.execute("DELETE FROM transcriptions WHERE file_path = ?", (audio_path,))
    else:
        conn.execute(
            "UPDATE transcriptions SET segments_json = NULL, status = 'pending' WHERE file_path = ?",
            (audio_path,),
        )
    return conn.total_changes


def main():
    parser = argparse.ArgumentParser(
        description="Delete transcription files and reset DB records for re-processing."
    )
    parser.add_argument("folder", type=Path, help="Folder to clean up")
    parser.add_argument("--recursive", action="store_true", help="Scan subfolders recursively")
    parser.add_argument("--delete-db", action="store_true", help="Delete DB records instead of resetting to pending")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()

    folder = args.folder.resolve()
    if not folder.is_dir():
        parser.error(f"Not a directory: {folder}")

    files = find_ai_data_files(folder, args.recursive)
    if not files:
        print(f"No .txt/.json files found in ai_data/ under {folder}")
        return

    db_action = "delete DB record" if args.delete_db else "reset to pending"
    print(f"Found {len(files)} file(s) — action: {db_action}\n")

    conn = sqlite3.connect(DB_PATH) if not args.dry_run else None

    deleted_files = 0
    db_updated = 0

    try:
        for f in files:
            audio_path = str(f.with_suffix(".mp3"))
            print(f"  {f.relative_to(folder)}", end="")

            if args.dry_run:
                print(f"  →  [dry-run] delete file + {db_action} for {f.name}")
                continue

            f.unlink()
            deleted_files += 1

            changes_before = conn.total_changes
            reset_db_record(conn, audio_path, args.delete_db)
            if conn.total_changes > changes_before:
                print(f"  →  deleted + DB {db_action}")
                db_updated += 1
            else:
                print(f"  →  deleted (no matching DB record)")

        if conn:
            conn.commit()
    finally:
        if conn:
            conn.close()

    if not args.dry_run:
        print(f"\nDone: {deleted_files} file(s) deleted, {db_updated} DB record(s) updated.")


if __name__ == "__main__":
    main()

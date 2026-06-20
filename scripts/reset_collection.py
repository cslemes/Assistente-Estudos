"""
Reset SQLite transcription status to 'pending' so the next POST /ingest
re-embeds everything after the Qdrant collection has been wiped.

Run AFTER scripts/create_collection.py.

Usage:
    python scripts/reset_collection.py           # dry-run
    python scripts/reset_collection.py --apply   # execute
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = os.path.join(os.getcwd(), "assistente.db")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Execute reset (default: dry-run)")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"DB not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM transcriptions WHERE status = 'sent'"
        ).fetchone()[0]

        if count == 0:
            print("No 'sent' rows to reset.")
            return

        if args.apply:
            conn.execute("UPDATE transcriptions SET status = 'pending' WHERE status = 'sent'")
            conn.commit()
            print(f"Reset {count} row(s) → 'pending'. Now call POST /ingest.")
        else:
            print(f"[dry-run] Would reset {count} row(s) from 'sent' → 'pending'.")
            print("Run with --apply to execute.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

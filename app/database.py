import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.getcwd(), "assistente.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path   TEXT NOT NULL UNIQUE,
                video_url   TEXT,
                text        TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                created_at  TEXT NOT NULL
            )
        """)
        try:
            conn.execute("ALTER TABLE transcriptions ADD COLUMN segments_json TEXT")
        except Exception:
            pass  # column already exists
        try:
            conn.execute("ALTER TABLE transcriptions ADD COLUMN summary TEXT")
        except Exception:
            pass  # column already exists


def insert_transcription(file_path: str, text: str, video_url: str = None, segments_json: str = None):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO transcriptions (file_path, video_url, text, segments_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                segments_json = excluded.segments_json,
                status = 'pending'
            """,
            (file_path, video_url, text, segments_json, datetime.now(timezone.utc).isoformat()),
        )


def has_segments(file_path: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT segments_json FROM transcriptions WHERE file_path = ?",
            (file_path,),
        ).fetchone()
    return bool(row and row["segments_json"])


def get_pending() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transcriptions WHERE status = 'pending' ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_transcriptions() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, file_path, video_url, status, summary, created_at FROM transcriptions ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def get_transcription(transcription_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM transcriptions WHERE id = ?",
            (transcription_id,),
        ).fetchone()
    return dict(row) if row else None


def get_unsummarized() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transcriptions WHERE summary IS NULL ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def set_summary(transcription_id: int, summary: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE transcriptions SET summary = ? WHERE id = ?",
            (summary, transcription_id),
        )


def set_status(transcription_id: int, status: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE transcriptions SET status = ? WHERE id = ?",
            (status, transcription_id),
        )


init_db()

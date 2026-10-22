import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from .config import settings


DB_PATH = settings.database_url.replace("sqlite:///", "")


def init_db():
    """Create tables if not exist."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                test_case TEXT NOT NULL,
                video_path TEXT,
                question TEXT,
                answer TEXT,
                answer_audio_path TEXT,
                timestamps_json TEXT,
                language TEXT,
                status TEXT,  -- success, partial, failed, uncertain
                evidence_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                type TEXT,  -- stt, ocr, image_assist, translation, tts
                input_ref TEXT,
                output_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            )
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def log_run(
    test_case: str,
    video_path: str,
    question: str,
    answer: str,
    answer_audio_path: str,
    timestamps: Dict[str, Any],
    language: str,
    status: str,
    evidence: List[Dict[str, Any]],
) -> str:
    run_id = str(uuid.uuid4())[:8]
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO runs (id, test_case, video_path, question, answer, answer_audio_path,
                              timestamps_json, language, status, evidence_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                test_case,
                video_path,
                question,
                answer,
                answer_audio_path,
                json.dumps(timestamps),
                language,
                status,
                json.dumps(evidence),
            ),
        )
        for ev in evidence:
            conn.execute(
                """
                INSERT INTO evidence (id, run_id, type, input_ref, output_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4())[:8],
                    run_id,
                    ev.get("type"),
                    ev.get("input_ref"),
                    json.dumps(ev.get("output")),
                ),
            )
    return run_id


def get_recent_runs(limit: int = 20) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# Initialize on import
init_db()
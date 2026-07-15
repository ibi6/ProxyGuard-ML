"""SQLite schema helpers for task history, predict logs, and settings."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS train_tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    models TEXT,
    config TEXT,
    progress REAL DEFAULT 0,
    metrics TEXT,
    best_model TEXT,
    error TEXT,
    message TEXT,
    created_at TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS predict_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    model TEXT,
    input_summary TEXT,
    predicted_label TEXT,
    confidence REAL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with Row factory enabled.

    check_same_thread=False allows background train workers to update task rows.
    """
    path = Path(db_path) if db_path is not None else Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> Path:
    """Create train_tasks / predict_logs / settings tables if missing.

    Returns the resolved database path.
    """
    path = Path(db_path) if db_path is not None else Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(path) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()
    return path

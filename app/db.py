"""SQLite：训练任务、预测日志、设置。"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import DB_PATH, LEGACY_DB_PATH

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

CREATE INDEX IF NOT EXISTS idx_train_tasks_status ON train_tasks(status);
CREATE INDEX IF NOT EXISTS idx_train_tasks_finished ON train_tasks(finished_at);
CREATE INDEX IF NOT EXISTS idx_train_tasks_created ON train_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_predict_logs_created ON predict_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_predict_logs_model ON predict_logs(model);
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


def _migrate_legacy_database(target: Path) -> None:
    """Copy the pre-v0.4 database into the persisted data directory once."""
    legacy = Path(LEGACY_DB_PATH)
    if target.exists() or not legacy.exists() or target.resolve() == legacy.resolve():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(legacy), timeout=30) as source:
        with sqlite3.connect(str(target), timeout=30) as destination:
            source.backup(destination)


def init_db(db_path: Path | None = None) -> Path:
    """Create train_tasks / predict_logs / settings tables if missing.

    Returns the resolved database path.
    """
    path = Path(db_path) if db_path is not None else Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    if db_path is None:
        _migrate_legacy_database(path)
    with get_connection(path) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()
    return path


def recover_interrupted_tasks(db_path: Path | None = None) -> int:
    """Mark training rows left running by a previous process as failed."""
    path = Path(db_path) if db_path is not None else Path(DB_PATH)
    init_db(path)
    finished_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    error = "training interrupted by service restart"
    message = "训练因服务重启中断，请重新启动训练"
    with get_connection(path) as conn:
        cursor = conn.execute(
            """
            UPDATE train_tasks
            SET status = 'failed', error = ?, message = ?, finished_at = ?
            WHERE status = 'running'
            """,
            (error, message, finished_at),
        )
        conn.commit()
        return max(0, int(cursor.rowcount))

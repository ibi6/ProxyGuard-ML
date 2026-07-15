-- ProxyGuard ML — SQLite schema (task / log / settings only)
-- This is an experiment-console store, not a multi-tenant enterprise IPAM schema.
-- Apply via app.db.init_db() at process start, or:
--   sqlite3 app/proxyguard.db < docs/schema.sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS train_tasks (
    task_id     TEXT PRIMARY KEY,
    status      TEXT NOT NULL,          -- running | success | failed
    models      TEXT,                  -- JSON list
    config      TEXT,                  -- JSON object (seed, ratios, dataset meta)
    progress    REAL DEFAULT 0,
    metrics     TEXT,                  -- JSON object per model
    best_model  TEXT,
    error       TEXT,
    message     TEXT,
    created_at  TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS predict_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT NOT NULL,
    model            TEXT,
    input_summary    TEXT,             -- JSON compact features
    predicted_label  TEXT,
    confidence       REAL,             -- NULL if model has no predict_proba
    details          TEXT              -- JSON full prediction row
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL                -- JSON-encoded scalar / list / object
);

CREATE INDEX IF NOT EXISTS idx_train_tasks_status
    ON train_tasks(status);
CREATE INDEX IF NOT EXISTS idx_train_tasks_finished
    ON train_tasks(finished_at);
CREATE INDEX IF NOT EXISTS idx_train_tasks_created
    ON train_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_predict_logs_created
    ON predict_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_predict_logs_model
    ON predict_logs(model);

-- Optional future tables (not required for current MVP):
-- datasets(id, source, n_per_class, seed, noise, path, created_at)
-- model_artifacts(name, path, sha256, trained_at, task_id)

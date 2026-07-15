"""SQLite-backed application settings."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from app.config import (
    RANDOM_SEED,
    TEST_RATIO,
    TRAIN_RATIO,
    USE_MOCK,
    VAL_RATIO,
)
from app.db import get_connection, init_db

_DEFAULT_SETTINGS: dict[str, Any] = {
    "random_seed": RANDOM_SEED,
    "train_ratio": TRAIN_RATIO,
    "val_ratio": VAL_RATIO,
    "test_ratio": TEST_RATIO,
    "default_models": ["random_forest", "xgboost", "lightgbm", "voting", "stacking"],
    "n_per_class_default": 1000,
    "noise_default": 0.85,
    "theme": "dark",
    "use_mock": USE_MOCK,
}


class SettingsService:
    """Persist settings as key/value JSON rows in SQLite."""

    def __init__(self) -> None:
        init_db()
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        with get_connection() as conn:
            for key, value in _DEFAULT_SETTINGS.items():
                row = conn.execute(
                    "SELECT key FROM settings WHERE key = ?", (key,)
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?)",
                        (key, json.dumps(value, ensure_ascii=False)),
                    )
            conn.commit()

    def get_settings(self) -> dict[str, Any]:
        out = deepcopy(_DEFAULT_SETTINGS)
        with get_connection() as conn:
            for row in conn.execute("SELECT key, value FROM settings").fetchall():
                try:
                    out[row["key"]] = json.loads(row["value"])
                except (TypeError, json.JSONDecodeError):
                    out[row["key"]] = row["value"]
        return out

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("settings payload must be an object")
        current = self.get_settings()
        with get_connection() as conn:
            for key, value in payload.items():
                if key not in _DEFAULT_SETTINGS:
                    continue
                current[key] = value
                conn.execute(
                    """
                    INSERT INTO settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, json.dumps(value, ensure_ascii=False)),
                )
            conn.commit()
        return current


settings_service = SettingsService()

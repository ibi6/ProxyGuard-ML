"""系统设置读写。"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from app.config import (
    RANDOM_SEED,
    TEST_RATIO,
    TRAIN_RATIO,
    VAL_RATIO,
)
from app.db import get_connection, init_db

# 只保留页面和训练真正会用到的项（不要 theme / use_mock 这种摆设字段）
_DEFAULT_SETTINGS: dict[str, Any] = {
    "random_seed": RANDOM_SEED,
    "train_ratio": TRAIN_RATIO,
    "val_ratio": VAL_RATIO,
    "test_ratio": TEST_RATIO,
    "n_per_class_default": 1000,
    "noise_default": 0.85,
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
                key = row["key"]
                if key not in _DEFAULT_SETTINGS:
                    continue  # 忽略历史遗留的 theme / use_mock 等
                try:
                    out[key] = json.loads(row["value"])
                except (TypeError, json.JSONDecodeError):
                    out[key] = row["value"]
        return out

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("settings payload must be an object")
        current = self.get_settings()
        # Merge then validate ratios/seed before writing (avoid half-saved bad state).
        merged = dict(current)
        for key, value in payload.items():
            if key in _DEFAULT_SETTINGS:
                merged[key] = value
        self._validate_merged(merged)
        with get_connection() as conn:
            for key in _DEFAULT_SETTINGS:
                if key not in payload and key not in merged:
                    continue
                value = merged[key]
                conn.execute(
                    """
                    INSERT INTO settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, json.dumps(value, ensure_ascii=False)),
                )
            conn.commit()
        return merged

    @staticmethod
    def _validate_merged(cfg: dict[str, Any]) -> None:
        try:
            seed = int(cfg.get("random_seed", RANDOM_SEED))
        except (TypeError, ValueError) as exc:
            raise ValueError("random_seed must be an integer") from exc
        if seed < 0:
            raise ValueError("random_seed must be >= 0")
        try:
            tr = float(cfg.get("train_ratio", TRAIN_RATIO))
            va = float(cfg.get("val_ratio", VAL_RATIO))
            te = float(cfg.get("test_ratio", TEST_RATIO))
        except (TypeError, ValueError) as exc:
            raise ValueError("train/val/test ratios must be numbers") from exc
        if min(tr, va, te) <= 0:
            raise ValueError("train/val/test ratios must be positive")
        total = tr + va + te
        if abs(total - 1.0) > 0.02:
            raise ValueError(
                f"train/val/test ratios must sum to 1.0 (got {total:.4f})"
            )
        try:
            n_per = int(cfg.get("n_per_class_default", 1000))
            noise = float(cfg.get("noise_default", 0.85))
        except (TypeError, ValueError) as exc:
            raise ValueError("n_per_class_default/noise_default invalid") from exc
        if n_per < 1:
            raise ValueError("n_per_class_default must be >= 1")
        if noise < 0:
            raise ValueError("noise_default must be >= 0")
        # Normalize ratios so training always receives a clean triple.
        cfg["random_seed"] = seed
        cfg["train_ratio"] = tr / total
        cfg["val_ratio"] = va / total
        cfg["test_ratio"] = te / total
        cfg["n_per_class_default"] = n_per
        cfg["noise_default"] = noise

    def get_split_ratios(self) -> tuple[float, float, float]:
        """Return (train, val, test) ratios from persisted settings."""
        cfg = self.get_settings()
        tr = float(cfg.get("train_ratio", TRAIN_RATIO))
        va = float(cfg.get("val_ratio", VAL_RATIO))
        te = float(cfg.get("test_ratio", TEST_RATIO))
        total = tr + va + te
        if total <= 0:
            return float(TRAIN_RATIO), float(VAL_RATIO), float(TEST_RATIO)
        return tr / total, va / total, te / total

    def get_random_seed(self) -> int:
        cfg = self.get_settings()
        try:
            return int(cfg.get("random_seed", RANDOM_SEED))
        except (TypeError, ValueError):
            return int(RANDOM_SEED)


settings_service = SettingsService()

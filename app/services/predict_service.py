"""Prediction service: real inference + SQLite predict_logs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.config import FEATURE_COLUMNS
from app.db import get_connection, init_db
from app.ml.predict import predict_samples


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class PredictService:
    """Load trained models, predict samples, and append predict_logs."""

    def __init__(self) -> None:
        init_db()

    def predict(
        self,
        samples: list[dict[str, Any]],
        model_name: str | None = None,
    ) -> dict[str, Any]:
        if not samples:
            raise ValueError("samples must not be empty")

        result = predict_samples(samples, model_name=model_name)
        self._log_predictions(samples, result)
        return result

    def _log_predictions(
        self,
        samples: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> None:
        model = result.get("model")
        created = _utcnow_iso()
        rows = []
        for sample, pred in zip(samples, result.get("predictions") or []):
            # Compact input summary (key features only)
            summary = {
                k: sample.get(k)
                for k in (
                    "pkt_len_mean",
                    "iat_mean",
                    "packets_per_second",
                    "pkt_size_entropy",
                    "byte_up_down_ratio",
                    "duration",
                )
                if k in sample or k in FEATURE_COLUMNS
            }
            rows.append(
                (
                    created,
                    model,
                    json.dumps(summary, ensure_ascii=False, default=str),
                    pred.get("label"),
                    float(pred.get("confidence") or 0.0),
                    json.dumps(pred, ensure_ascii=False, default=str),
                )
            )
        if not rows:
            return
        with get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO predict_logs (
                    created_at, model, input_summary, predicted_label, confidence, details
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

    def recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        with get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, created_at, model, input_summary, predicted_label, confidence, details
                FROM predict_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            out = []
            for row in cur.fetchall():
                out.append(
                    {
                        "id": row["id"],
                        "created_at": row["created_at"],
                        "model": row["model"],
                        "input_summary": json.loads(row["input_summary"] or "{}"),
                        "predicted_label": row["predicted_label"],
                        "confidence": row["confidence"],
                        "details": json.loads(row["details"] or "{}"),
                    }
                )
            return out


predict_service = PredictService()

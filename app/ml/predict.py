"""Load trained joblib models and run batch inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.config import FEATURE_COLUMNS, LABEL_DISPLAY, LABELS, MODELS_DIR, REPORTS_DIR


def resolve_model_name(model_name: str | None = None) -> str:
    """Pick best_model from metrics report, else first available joblib."""
    if model_name:
        return model_name

    metrics_path = REPORTS_DIR / "metrics.json"
    if metrics_path.exists():
        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8"))
            best = payload.get("best_model")
            if best and (MODELS_DIR / f"{best}.joblib").exists():
                return str(best)
        except (OSError, json.JSONDecodeError):
            pass

    if MODELS_DIR.exists():
        paths = sorted(MODELS_DIR.glob("*.joblib"))
        if paths:
            return paths[0].stem

    raise FileNotFoundError(
        "no trained model found; train models first or pass model_name"
    )


def load_model(model_name: str | None = None) -> tuple[Any, str, Path]:
    """Load a joblib model. Returns (estimator, resolved_name, path)."""
    name = resolve_model_name(model_name)
    path = MODELS_DIR / f"{name}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"model file not found: {path}")
    model = joblib.load(path)
    return model, name, path


def _samples_to_frame(samples: list[dict[str, Any]]) -> pd.DataFrame:
    if not samples:
        raise ValueError("samples must not be empty")
    rows: list[dict[str, float]] = []
    for i, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise ValueError(f"sample[{i}] must be an object")
        row: dict[str, float] = {}
        for col in FEATURE_COLUMNS:
            if col not in sample:
                raise ValueError(f"sample[{i}] missing feature: {col}")
            try:
                row[col] = float(sample[col])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"sample[{i}].{col} is not numeric") from exc
        rows.append(row)
    return pd.DataFrame(rows, columns=list(FEATURE_COLUMNS))


def _proba_maps(model: Any, X: pd.DataFrame) -> list[dict[str, float]] | None:
    if not hasattr(model, "predict_proba"):
        return None
    try:
        proba = np.asarray(model.predict_proba(X), dtype=float)
    except Exception:  # noqa: BLE001 — some estimators lack proba at runtime
        return None

    classes = getattr(model, "classes_", None)
    if classes is None:
        classes = list(LABELS)
    else:
        classes = [str(c) for c in list(classes)]

    maps: list[dict[str, float]] = []
    for row in proba:
        m = {lab: 0.0 for lab in LABELS}
        for j, lab in enumerate(classes):
            if j < len(row):
                m[str(lab)] = float(row[j])
        # renormalize tiny drift
        total = sum(m.values()) or 1.0
        maps.append({k: round(v / total, 6) for k, v in m.items()})
    return maps


def predict_samples(
    samples: list[dict[str, Any]],
    model_name: str | None = None,
) -> dict[str, Any]:
    """Run inference on feature dicts. Returns frontend-compatible payload."""
    model, name, _path = load_model(model_name)
    X = _samples_to_frame(samples)
    y_pred = [str(x) for x in model.predict(X)]
    proba_maps = _proba_maps(model, X)

    predictions: list[dict[str, Any]] = []
    for i, label in enumerate(y_pred):
        if proba_maps is not None:
            proba = proba_maps[i]
            confidence = float(proba.get(label, max(proba.values()) if proba else 0.0))
            conf_out = round(float(confidence), 4)
            proba_support = True
        else:
            # Do NOT invent a fake confidence (e.g. 0.85) — that misleads demos.
            conf_out = None
            proba = {lab: None for lab in LABELS}
            proba_support = False

        predictions.append(
            {
                "index": i,
                "label": label,
                "display_label": LABEL_DISPLAY.get(label, label),
                "confidence": conf_out,
                "probabilities": proba,
                "proba_supported": proba_support,
                "model": name,
            }
        )

    return {
        "predictions": predictions,
        "model": name,
        "count": len(predictions),
        "mode": "real",
    }

from __future__ import annotations

import pandas as pd

from app.config import FEATURE_COLUMNS  # re-export
from app.ml.labels import normalize_label


def validate_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    if "label" not in df.columns:
        raise ValueError("missing required column: label")
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing feature columns: {missing}")
    out = df[FEATURE_COLUMNS + ["label"]].copy()
    out["label"] = out["label"].map(normalize_label)
    for c in FEATURE_COLUMNS:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if out[FEATURE_COLUMNS].isna().any().any():
        raise ValueError("feature columns contain non-numeric or NaN values")
    return out.reset_index(drop=True)

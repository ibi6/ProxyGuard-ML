"""Train model zoo, evaluate, and persist artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from app.config import (
    FEATURE_COLUMNS,
    FIGURES_DIR,
    LABELS,
    MODELS_DIR,
    RANDOM_SEED,
    REPORTS_DIR,
    TEST_RATIO,
    TRAIN_RATIO,
    VAL_RATIO,
)
from app.ml.evaluate import (
    evaluate_model,
    export_experiment_figures,
    save_metrics_report,
)
from app.ml.features import validate_feature_frame
from app.ml.models import (
    INTEGER_LABEL_MODELS,
    LabeledClassifier,
    build_model,
    get_model_zoo,
)


def _split_ratios(
    ratios: Sequence[float] | None,
) -> tuple[float, float, float]:
    if ratios is None:
        return float(TRAIN_RATIO), float(VAL_RATIO), float(TEST_RATIO)
    if len(ratios) != 3:
        raise ValueError("ratios must be a 3-tuple (train, val, test)")
    tr, va, te = (float(ratios[0]), float(ratios[1]), float(ratios[2]))
    total = tr + va + te
    if total <= 0:
        raise ValueError("ratios must sum to a positive value")
    # Normalize slight floating drift
    return tr / total, va / total, te / total


def _extract_feature_importances(
    model: Any,
    feature_names: Sequence[str],
) -> dict[str, float] | None:
    """Pull feature_importances_ when available (trees / boosting / pipelines)."""
    names = list(feature_names)
    estimator = model
    # Unwrap LabeledClassifier first (boosters that encode string labels)
    if hasattr(estimator, "estimator") and hasattr(estimator, "label_encoder"):
        estimator = estimator.estimator
    # Unwrap common Pipeline final step
    named = getattr(estimator, "named_steps", None)
    if named:
        steps = list(named.values())
        estimator = steps[-1] if steps else estimator

    importances = None
    if hasattr(estimator, "feature_importances_"):
        importances = np.asarray(estimator.feature_importances_, dtype=float)
    elif hasattr(estimator, "coef_"):
        coef = np.asarray(estimator.coef_, dtype=float)
        importances = np.mean(np.abs(coef), axis=0) if coef.ndim > 1 else np.abs(coef)

    if importances is None or importances.size != len(names):
        return None

    total = float(importances.sum())
    if total > 0:
        importances = importances / total
    return {n: float(v) for n, v in zip(names, importances)}


def train_all(
    df: pd.DataFrame,
    model_names: Iterable[str] | None = None,
    seed: int = RANDOM_SEED,
    ratios: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Train selected models, evaluate on held-out test, persist joblib + metrics.

    Returns:
        {
          "models": {name: path_str},
          "metrics": {name: {accuracy, precision, recall, f1, ...}},
          "best_model": str,
          "feature_importances": {name: {feat: weight} | {}},
          "confusion_matrices": {name: nested list},
        }
    """
    frame = validate_feature_frame(df)
    train_r, val_r, test_r = _split_ratios(ratios)

    names = list(model_names) if model_names is not None else list(get_model_zoo().keys())
    if not names:
        raise ValueError("model_names must not be empty")
    unknown = [n for n in names if n not in get_model_zoo()]
    if unknown:
        raise ValueError(f"unknown model(s): {unknown}")

    X = frame[list(FEATURE_COLUMNS)]
    y = frame["label"].astype(str)

    # First carve out test; remaining split into train/val (val reserved for future tuning)
    X_temp, X_test, y_temp, y_test = train_test_split(
        X,
        y,
        test_size=test_r,
        random_state=seed,
        stratify=y,
    )
    val_share = val_r / (train_r + val_r) if (train_r + val_r) > 0 else 0.0
    if val_share > 0:
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp,
            y_temp,
            test_size=val_share,
            random_state=seed,
            stratify=y_temp,
        )
    else:
        X_train, y_train = X_temp, y_temp
        X_val, y_val = None, None  # noqa: F841 — reserved

    # For tree boosters that prefer integer labels (XGBoost), encode when needed.
    # sklearn estimators accept string labels; XGB/LGBM also do in recent versions.
    # Keep string labels for consistency with evaluate_model / LABELS order.
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    models_paths: dict[str, str] = {}
    metrics_map: dict[str, dict[str, Any]] = {}
    fi_map: dict[str, dict[str, float]] = {}
    cm_map: dict[str, list] = {}

    label_list = list(LABELS)

    for name in names:
        model = build_model(name, seed=seed)

        # XGBoost/LightGBM fit on int codes; wrap so predict/joblib emit string LABELS.
        # Never assign classes_ on the raw booster (read-only on XGBClassifier).
        if name in INTEGER_LABEL_MODELS:
            model = LabeledClassifier(model, labels=label_list)

        model.fit(X_train, y_train)

        m = evaluate_model(model, X_test, y_test, labels=label_list)
        # Flatten public metrics (keep cm separately in result)
        public = {
            "accuracy": m["accuracy"],
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1"],
        }
        metrics_map[name] = public
        cm_map[name] = m["confusion_matrix"]

        fi = _extract_feature_importances(model, FEATURE_COLUMNS)
        fi_map[name] = fi or {}

        out_path = MODELS_DIR / f"{name}.joblib"
        joblib.dump(model, out_path)
        models_paths[name] = str(out_path)

    best_model = max(metrics_map.keys(), key=lambda n: metrics_map[n]["f1"])

    result: dict[str, Any] = {
        "models": models_paths,
        "metrics": metrics_map,
        "best_model": best_model,
        "feature_importances": fi_map,
        "confusion_matrices": cm_map,
        "labels": label_list,
        "feature_columns": list(FEATURE_COLUMNS),
        "seed": seed,
        "ratios": {"train": train_r, "val": val_r, "test": test_r},
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }

    # Paper-ready figures for offline reports + Web export bundle
    figure_paths = export_experiment_figures(result, out_dir=FIGURES_DIR)
    result["figures"] = figure_paths

    save_metrics_report(result)
    return result

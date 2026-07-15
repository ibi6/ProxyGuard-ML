"""训练模型、算测试集指标、保存 joblib 和图表。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Iterable, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

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

ProgressCallback = Callable[[float, str], None]


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


def _fit_decision_tree_with_val(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame | None,
    y_val: pd.Series | None,
    seed: int,
    labels: Sequence[str],
) -> tuple[Any, int | None, float | None]:
    """Pick max_depth on validation F1 when val set exists; else default depth 10."""
    depths = (4, 6, 8, 10, 12)
    if X_val is None or y_val is None or len(y_val) == 0:
        model = DecisionTreeClassifier(max_depth=10, random_state=seed)
        model.fit(X_train, y_train)
        return model, 10, None

    best_model = None
    best_depth = depths[0]
    best_score = -1.0
    for depth in depths:
        cand = DecisionTreeClassifier(max_depth=depth, random_state=seed)
        cand.fit(X_train, y_train)
        pred = cand.predict(X_val)
        score = float(
            f1_score(y_val, pred, labels=list(labels), average="macro", zero_division=0)
        )
        if score > best_score:
            best_score = score
            best_model = cand
            best_depth = depth
    assert best_model is not None
    return best_model, best_depth, best_score


def train_all(
    df: pd.DataFrame,
    model_names: Iterable[str] | None = None,
    seed: int = RANDOM_SEED,
    ratios: Sequence[float] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Train selected models, evaluate on held-out test, persist joblib + metrics.

    ``progress_callback(progress_0_to_1, message)`` is optional for UI polling.

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

    # Stratified split needs enough samples per class (train/val/test).
    counts = frame["label"].value_counts()
    if int(counts.min()) < 3:
        raise ValueError(
            "each class needs at least 3 samples for stratified train/val/test splits; "
            f"min class count={int(counts.min())}"
        )
    if len(frame) < 40:
        raise ValueError(
            f"dataset too small ({len(frame)} rows); generate/upload at least 40 samples"
        )

    X = frame[list(FEATURE_COLUMNS)]
    y = frame["label"].astype(str)

    # Stratified train / val / test. Val is used for light model selection when
    # multiple depths are compared for tree baselines; final metrics always on test.
    X_temp, X_test, y_temp, y_test = train_test_split(
        X,
        y,
        test_size=test_r,
        random_state=seed,
        stratify=y,
    )
    val_share = val_r / (train_r + val_r) if (train_r + val_r) > 0 else 0.0
    if val_share > 0 and len(y_temp) >= 8:
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp,
            y_temp,
            test_size=val_share,
            random_state=seed,
            stratify=y_temp,
        )
    else:
        X_train, y_train = X_temp, y_temp
        X_val, y_val = None, None

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
    tuned: dict[str, Any] = {}
    n_models = len(names)

    def _progress(frac: float, message: str) -> None:
        if progress_callback is not None:
            progress_callback(max(0.0, min(1.0, float(frac))), message)

    _progress(0.02, "split dataset")

    for idx, name in enumerate(names):
        _progress(0.05 + 0.85 * (idx / max(n_models, 1)), f"training {name}")

        selected_depth: int | None = None
        if name == "decision_tree":
            model, selected_depth, _val_tune = _fit_decision_tree_with_val(
                X_train, y_train, X_val, y_val, seed, label_list
            )
            if selected_depth is not None:
                tuned[name] = {"max_depth": selected_depth, "val_f1_tune": _val_tune}
        else:
            model = build_model(name, seed=seed)
            # XGBoost/LightGBM fit on int codes; wrap so predict/joblib emit string LABELS.
            if name in INTEGER_LABEL_MODELS:
                model = LabeledClassifier(model, labels=label_list)
            model.fit(X_train, y_train)

        val_f1 = None
        if X_val is not None and y_val is not None and len(y_val):
            try:
                y_val_pred = model.predict(X_val)
                val_f1 = float(
                    f1_score(
                        y_val,
                        y_val_pred,
                        labels=label_list,
                        average="macro",
                        zero_division=0,
                    )
                )
            except Exception:  # noqa: BLE001
                val_f1 = None

        m = evaluate_model(model, X_test, y_test, labels=label_list)
        public = {
            "accuracy": m["accuracy"],
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1"],
        }
        if val_f1 is not None:
            public["val_f1"] = val_f1
        if name in tuned and tuned[name].get("max_depth") is not None:
            public["tuned_max_depth"] = tuned[name]["max_depth"]
        metrics_map[name] = public
        cm_map[name] = m["confusion_matrix"]

        fi = _extract_feature_importances(model, FEATURE_COLUMNS)
        fi_map[name] = fi or {}

        out_path = MODELS_DIR / f"{name}.joblib"
        joblib.dump(model, out_path)
        models_paths[name] = f"models/{name}.joblib"
        _progress(0.05 + 0.85 * ((idx + 1) / max(n_models, 1)), f"finished {name}")

    best_model = max(metrics_map.keys(), key=lambda n: metrics_map[n]["f1"])
    _progress(0.92, "export figures")

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
        "n_val": int(len(X_val)) if X_val is not None else 0,
        "n_test": int(len(X_test)),
        "tuning": tuned,
        "eval_protocol": (
            "Models fit on train; decision_tree max_depth selected on val F1 when available; "
            "public accuracy/F1 reported on held-out test only."
        ),
    }

    # Paper-ready figures for offline reports + Web export bundle
    figure_paths = export_experiment_figures(result, out_dir=FIGURES_DIR)
    result["figures"] = figure_paths

    save_metrics_report(result)
    return result

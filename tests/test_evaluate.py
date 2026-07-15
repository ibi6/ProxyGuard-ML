"""TDD tests for evaluate_model and metrics reporting."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from app.config import FEATURE_COLUMNS, LABELS
from app.ml.data_generator import generate_synthetic_dataset
from app.ml.evaluate import (
    evaluate_model,
    export_experiment_figures,
    save_metrics_report,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split


def _tiny_split(seed: int = 42):
    df = generate_synthetic_dataset(n_per_class=50, seed=seed, noise=0.1)
    X = df[list(FEATURE_COLUMNS)].to_numpy(dtype=float)
    y = df["label"].to_numpy()
    return train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)


def test_evaluate_model_metrics_keys():
    X_train, X_test, y_train, y_test = _tiny_split()
    model = RandomForestClassifier(n_estimators=20, random_state=42)
    model.fit(X_train, y_train)

    metrics = evaluate_model(model, X_test, y_test, labels=list(LABELS))

    for key in ("accuracy", "precision", "recall", "f1"):
        assert key in metrics
        assert 0.0 <= float(metrics[key]) <= 1.0

    assert "confusion_matrix" in metrics
    cm = np.asarray(metrics["confusion_matrix"])
    assert cm.shape == (len(LABELS), len(LABELS))


def test_save_metrics_report_writes_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reports_dir = tmp_path / "reports"
    figures_dir = reports_dir / "figures"
    reports_dir.mkdir()
    figures_dir.mkdir()
    monkeypatch.setattr("app.ml.evaluate.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.ml.evaluate.FIGURES_DIR", figures_dir)

    payload = {
        "metrics": {"random_forest": {"accuracy": 0.9, "f1": 0.88, "precision": 0.89, "recall": 0.87}},
        "best_model": "random_forest",
        "confusion_matrices": {"random_forest": [[1, 0], [0, 1]]},
        "feature_importances": {"random_forest": {"pkt_len_mean": 0.1}},
    }
    path = save_metrics_report(payload)
    assert path.exists()
    assert path == reports_dir / "metrics.json"
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["best_model"] == "random_forest"
    assert "random_forest" in loaded["metrics"]


def test_export_experiment_figures_writes_required_pngs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    monkeypatch.setattr("app.ml.evaluate.FIGURES_DIR", figures_dir)

    result = {
        "metrics": {
            "decision_tree": {
                "accuracy": 0.9,
                "precision": 0.9,
                "recall": 0.9,
                "f1": 0.9,
            },
            "random_forest": {
                "accuracy": 0.95,
                "precision": 0.94,
                "recall": 0.93,
                "f1": 0.94,
            },
        },
        "best_model": "random_forest",
        "labels": list(LABELS),
        "confusion_matrices": {
            "random_forest": [
                [5, 0, 0, 0],
                [0, 5, 0, 0],
                [0, 0, 5, 0],
                [0, 0, 0, 5],
            ],
            "decision_tree": [
                [4, 1, 0, 0],
                [0, 4, 1, 0],
                [0, 0, 5, 0],
                [0, 0, 0, 5],
            ],
        },
        "feature_importances": {
            "random_forest": {
                "pkt_len_mean": 0.2,
                "iat_mean": 0.15,
                "total_bytes": 0.1,
                "pkt_size_entropy": 0.05,
            }
        },
    }

    paths = export_experiment_figures(result, out_dir=figures_dir)
    assert paths["model_accuracy_comparison"]
    assert paths["model_f1_comparison"]
    assert paths["confusion_matrix_best"]
    assert paths["feature_importance"]

    assert (figures_dir / "model_accuracy_comparison.png").exists()
    assert (figures_dir / "model_f1_comparison.png").exists()
    assert (figures_dir / "confusion_matrix_random_forest.png").exists()
    assert (figures_dir / "feature_importance.png").exists()

"""TDD tests for model zoo and train_all (small samples, fast)."""

from __future__ import annotations

from pathlib import Path

import joblib
import pytest

from app.config import FEATURE_COLUMNS, LABELS, MODELS_DIR
from app.ml.data_generator import generate_synthetic_dataset
from app.ml.models import build_model, get_model_zoo
from app.ml.train import train_all


EXPECTED_MODELS = {
    "decision_tree",
    "svm",
    "random_forest",
    "adaboost",
    "xgboost",
    "lightgbm",
    "voting",
    "stacking",
}


def test_get_model_zoo_covers_all_names():
    zoo = get_model_zoo()
    assert set(zoo.keys()) == EXPECTED_MODELS
    for name, display in zoo.items():
        assert isinstance(display, str) and display


@pytest.mark.parametrize("name", sorted(EXPECTED_MODELS))
def test_build_model_returns_estimator(name: str):
    est = build_model(name, seed=42)
    assert hasattr(est, "fit")
    assert hasattr(est, "predict")


def test_build_model_unknown_raises():
    with pytest.raises(ValueError, match="unknown model"):
        build_model("not_a_model")


def test_train_all_small(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir()

    monkeypatch.setattr("app.ml.train.MODELS_DIR", models_dir)
    monkeypatch.setattr("app.ml.train.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.ml.train.FIGURES_DIR", figures_dir)
    monkeypatch.setattr("app.ml.evaluate.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.ml.evaluate.FIGURES_DIR", figures_dir)

    df = generate_synthetic_dataset(n_per_class=80, seed=42, noise=0.1)
    result = train_all(df, ["random_forest", "voting"], seed=42)

    assert "random_forest" in result["metrics"]
    assert "voting" in result["metrics"]
    assert 0.0 <= result["metrics"]["random_forest"]["accuracy"] <= 1.0
    assert 0.0 <= result["metrics"]["random_forest"]["f1"] <= 1.0
    assert result["best_model"] in result["metrics"]

    assert "models" in result
    assert Path(result["models"]["random_forest"]).exists()
    assert Path(result["models"]["voting"]).exists()
    loaded = joblib.load(result["models"]["random_forest"])
    assert hasattr(loaded, "predict")

    assert "feature_importances" in result
    assert "confusion_matrices" in result
    assert result["best_model"] in result["confusion_matrices"]

    metrics_path = reports_dir / "metrics.json"
    assert metrics_path.exists()


def test_train_all_default_ratios(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir()
    monkeypatch.setattr("app.ml.train.MODELS_DIR", models_dir)
    monkeypatch.setattr("app.ml.train.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.ml.train.FIGURES_DIR", figures_dir)
    monkeypatch.setattr("app.ml.evaluate.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.ml.evaluate.FIGURES_DIR", figures_dir)

    df = generate_synthetic_dataset(n_per_class=40, seed=7, noise=0.1)
    result = train_all(df, ["decision_tree"], seed=7, ratios=(0.7, 0.15, 0.15))
    assert result["best_model"] == "decision_tree"
    assert set(FEATURE_COLUMNS).issubset(set(df.columns))
    assert set(df["label"].unique()) == set(LABELS)


@pytest.mark.parametrize("name", ["xgboost", "lightgbm"])
def test_train_all_booster_joblib_predicts_string_labels(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Regression: reloaded XGB/LGBM must predict LABELS strings, not int codes."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir()
    monkeypatch.setattr("app.ml.train.MODELS_DIR", models_dir)
    monkeypatch.setattr("app.ml.train.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.ml.train.FIGURES_DIR", figures_dir)
    monkeypatch.setattr("app.ml.evaluate.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.ml.evaluate.FIGURES_DIR", figures_dir)

    df = generate_synthetic_dataset(n_per_class=60, seed=42, noise=0.1)
    result = train_all(df, [name], seed=42)
    assert name in result["metrics"]
    assert 0.0 <= result["metrics"][name]["f1"] <= 1.0

    path = Path(result["models"][name])
    assert path.exists()
    loaded = joblib.load(path)
    assert hasattr(loaded, "predict")

    X = df[list(FEATURE_COLUMNS)].head(12)
    preds = loaded.predict(X)
    assert len(preds) == 12
    label_set = set(LABELS)
    for p in preds:
        assert isinstance(p, str), f"expected string label, got {type(p)!r}: {p!r}"
        assert p in label_set

    classes = getattr(loaded, "classes_", None)
    assert classes is not None
    assert set(map(str, classes)) == label_set

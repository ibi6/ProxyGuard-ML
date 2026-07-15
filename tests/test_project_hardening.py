"""Regression tests for hardening: settings→train, upload limits, auth, features."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import FEATURE_COLUMNS
from app.db import init_db
from app.main import app
from app.ml.features import validate_feature_frame


def _iso_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    data_dir = tmp_path / "data"
    models_dir = tmp_path / "models"
    reports_dir = tmp_path / "reports"
    figures_dir = reports_dir / "figures"
    db_path = tmp_path / "proxyguard.db"
    for d in (data_dir, models_dir, reports_dir, figures_dir):
        d.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("USE_MOCK", "false")
    monkeypatch.setattr("app.config.USE_MOCK", False)
    monkeypatch.setattr("app.config.DATA_DIR", data_dir)
    monkeypatch.setattr("app.config.MODELS_DIR", models_dir)
    monkeypatch.setattr("app.config.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.config.FIGURES_DIR", figures_dir)
    monkeypatch.setattr("app.config.DB_PATH", db_path)
    monkeypatch.setattr("app.db.DB_PATH", db_path)
    monkeypatch.setattr("app.ml.train.MODELS_DIR", models_dir)
    monkeypatch.setattr("app.ml.train.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.ml.train.FIGURES_DIR", figures_dir)
    monkeypatch.setattr("app.ml.evaluate.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.ml.evaluate.FIGURES_DIR", figures_dir)
    monkeypatch.setattr("app.ml.predict.MODELS_DIR", models_dir)
    monkeypatch.setattr("app.ml.predict.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.services.train_service.MODELS_DIR", models_dir)
    monkeypatch.setattr("app.services.train_service.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.services.experiment_service.REPORTS_DIR", reports_dir)
    monkeypatch.setattr("app.services.experiment_service.FIGURES_DIR", figures_dir)

    from app.services.dataset_service import DatasetService
    from app.services.experiment_service import ExperimentService
    from app.services.predict_service import PredictService
    from app.services.settings_service import SettingsService
    from app.services.train_service import TrainService

    ds = DatasetService(data_dir=data_dir)
    monkeypatch.setattr("app.services.dataset_service.dataset_service", ds)
    monkeypatch.setattr("app.api.data.dataset_service", ds)
    monkeypatch.setattr("app.services.train_service.dataset_service", ds)
    monkeypatch.setattr("app.services.experiment_service.dataset_service", ds)

    init_db(db_path)
    ts = TrainService()
    ps = PredictService()
    es = ExperimentService()
    ss = SettingsService()
    monkeypatch.setattr("app.services.train_service.train_service", ts)
    monkeypatch.setattr("app.api.train.train_service", ts)
    monkeypatch.setattr("app.services.train_service.settings_service", ss)
    monkeypatch.setattr("app.services.predict_service.predict_service", ps)
    monkeypatch.setattr("app.api.predict.predict_service", ps)
    monkeypatch.setattr("app.services.experiment_service.experiment_service", es)
    monkeypatch.setattr("app.api.experiments.experiment_service", es)
    monkeypatch.setattr("app.services.settings_service.settings_service", ss)
    monkeypatch.setattr("app.api.settings.settings_service", ss)

    return TestClient(app), ts, ss


def test_validate_rejects_inf():
    row = {c: 1.0 for c in FEATURE_COLUMNS}
    row["label"] = "vmess"
    row["pkt_len_mean"] = float("inf")
    with pytest.raises(ValueError, match="Inf|finite"):
        validate_feature_frame(pd.DataFrame([row]))


def test_settings_ratio_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    client, _ts, ss = _iso_client(tmp_path, monkeypatch)
    with client:
        bad = client.put(
            "/api/settings",
            json={"train_ratio": 0.5, "val_ratio": 0.5, "test_ratio": 0.5},
        )
        assert bad.status_code == 400
        ok = client.put(
            "/api/settings",
            json={
                "random_seed": 7,
                "train_ratio": 0.6,
                "val_ratio": 0.2,
                "test_ratio": 0.2,
            },
        )
        assert ok.status_code == 200
        body = ok.json()
        assert abs(body["train_ratio"] + body["val_ratio"] + body["test_ratio"] - 1.0) < 1e-6
        assert ss.get_random_seed() == 7
        tr, va, te = ss.get_split_ratios()
        assert abs(tr - 0.6) < 1e-6 and abs(va - 0.2) < 1e-6 and abs(te - 0.2) < 1e-6


def test_upload_rejects_non_csv_and_oversize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    client, _ts, _ss = _iso_client(tmp_path, monkeypatch)
    monkeypatch.setattr("app.api.data.MAX_UPLOAD_BYTES", 64)
    with client:
        r = client.post(
            "/api/data/upload",
            files={"file": ("x.txt", b"a,b\n1,2\n", "text/plain")},
        )
        assert r.status_code == 400
        r2 = client.post(
            "/api/data/upload",
            files={"file": ("x.csv", b"x" * 200, "text/csv")},
        )
        assert r2.status_code == 413


def test_train_uses_settings_ratios(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    client, ts, ss = _iso_client(tmp_path, monkeypatch)
    with client:
        ss.update_settings(
            {"random_seed": 11, "train_ratio": 0.5, "val_ratio": 0.25, "test_ratio": 0.25}
        )
        gen = client.post(
            "/api/data/generate",
            json={"n_per_class": 40, "seed": 11, "noise": 0.85},
        )
        assert gen.status_code == 200
        start = client.post("/api/train", json={"models": ["decision_tree"]})
        assert start.status_code == 200
        task_id = start.json()["task_id"]
        # poll
        import time

        for _ in range(60):
            t = client.get(f"/api/train/{task_id}").json()
            if t["status"] in ("success", "failed"):
                break
            time.sleep(0.25)
        assert t["status"] == "success"
        cfg = t.get("config") or {}
        ratios = cfg.get("ratios") or {}
        assert abs(float(ratios["train"]) - 0.5) < 1e-6
        assert abs(float(ratios["val"]) - 0.25) < 1e-6
        assert abs(float(ratios["test"]) - 0.25) < 1e-6


def test_train_mutex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    client, ts, _ss = _iso_client(tmp_path, monkeypatch)

    class SlowThread:
        def is_alive(self):
            return True

    with client:
        client.post(
            "/api/data/generate",
            json={"n_per_class": 30, "seed": 1, "noise": 0.85},
        )
        # Simulate an in-flight worker
        ts._threads["task_busy"] = SlowThread()  # type: ignore[assignment]
        r = client.post("/api/train", json={"models": ["decision_tree"]})
        assert r.status_code == 400
        assert "running" in r.json()["detail"].lower()


def test_api_token_blocks_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.config.API_TOKEN", "secret-token")
    monkeypatch.setattr("app.security.API_TOKEN", "secret-token")
    client, _ts, _ss = _iso_client(tmp_path, monkeypatch)
    with client:
        denied = client.post(
            "/api/data/generate",
            json={"n_per_class": 10, "seed": 1, "noise": 0.5},
        )
        assert denied.status_code == 401
        ok = client.post(
            "/api/data/generate",
            json={"n_per_class": 10, "seed": 1, "noise": 0.5},
            headers={"X-API-Token": "secret-token"},
        )
        assert ok.status_code == 200


def test_predict_stats_and_health(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    client, _ts, _ss = _iso_client(tmp_path, monkeypatch)
    with client:
        h = client.get("/api/health").json()
        assert h["status"] == "ok"
        assert "use_mock" in h
        assert "auth_required" in h
        s = client.get("/api/predict/stats").json()
        assert s["count"] == 0
        sysinfo = client.get("/api/system").json()
        assert sysinfo["service"] == "ProxyGuard ML"
        assert "dataset" in sysinfo
        assert "settings" in sysinfo


def test_decision_tree_val_tuning_records_depth():
    from app.ml.data_generator import generate_synthetic_dataset
    from app.ml.train import train_all

    df = generate_synthetic_dataset(n_per_class=80, seed=42, noise=0.85)
    progress_msgs: list[str] = []

    def cb(p: float, msg: str) -> None:
        progress_msgs.append(msg)

    result = train_all(
        df,
        model_names=["decision_tree", "random_forest"],
        seed=42,
        ratios=(0.7, 0.15, 0.15),
        progress_callback=cb,
    )
    assert "decision_tree" in result["metrics"]
    assert result["metrics"]["decision_tree"].get("tuned_max_depth") is not None
    assert result["metrics"]["random_forest"].get("tuned_n_estimators") is not None
    assert result.get("n_val", 0) > 0
    assert any("decision_tree" in m for m in progress_msgs)


def test_train_cancel_between_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app.ml.train import TrainingCancelled, train_all
    from app.ml.data_generator import generate_synthetic_dataset

    df = generate_synthetic_dataset(n_per_class=40, seed=1, noise=0.5)
    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 2

    with pytest.raises(TrainingCancelled):
        train_all(
            df,
            model_names=["decision_tree", "random_forest", "svm"],
            seed=1,
            should_cancel=should_cancel,
        )

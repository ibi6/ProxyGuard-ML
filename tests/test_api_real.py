"""End-to-end real API path: generate -> train (poll) -> experiments -> predict."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolate data/models/reports/db under tmp_path for a clean real run."""
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

    # Rebuild singletons against isolated paths
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
    monkeypatch.setattr("app.services.predict_service.predict_service", ps)
    monkeypatch.setattr("app.api.predict.predict_service", ps)
    monkeypatch.setattr("app.services.experiment_service.experiment_service", es)
    monkeypatch.setattr("app.api.experiments.experiment_service", es)
    monkeypatch.setattr("app.services.settings_service.settings_service", ss)
    monkeypatch.setattr("app.api.settings.settings_service", ss)

    with TestClient(app) as c:
        yield c


def _sample() -> dict:
    return {
        "pkt_len_mean": 600,
        "pkt_len_std": 120,
        "pkt_len_min": 40,
        "pkt_len_max": 1400,
        "pkt_len_p25": 500,
        "pkt_len_p75": 700,
        "iat_mean": 0.02,
        "iat_std": 0.01,
        "iat_burstiness": 0.3,
        "uplink_pkt_ratio": 0.45,
        "byte_up_down_ratio": 1.1,
        "duration": 8.0,
        "total_packets": 200,
        "total_bytes": 120000,
        "packets_per_second": 25,
        "pkt_size_entropy": 3.2,
        "iat_entropy": 2.8,
    }


def _poll_train(client: TestClient, task_id: str, timeout: float = 180.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get(f"/api/train/{task_id}")
        assert r.status_code == 200
        last = r.json()
        if last["status"] in {"success", "failed"}:
            return last
        time.sleep(0.5)
    raise AssertionError(f"train task {task_id} timed out; last={last}")


def test_real_generate_train_experiments_predict(client: TestClient):
    # generate
    r = client.post(
        "/api/data/generate",
        json={"n_per_class": 60, "seed": 42, "noise": 0.1},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_samples"] == 240

    # train without data should fail when empty — already have data
    r = client.post(
        "/api/train",
        json={"models": ["decision_tree", "random_forest"]},
    )
    assert r.status_code == 200
    payload = r.json()
    assert "task_id" in payload
    # Must return quickly (async): status is running or already finished
    assert payload["status"] in {"running", "success"}
    task_id = payload["task_id"]

    task = _poll_train(client, task_id, timeout=180.0)
    assert task["status"] == "success", task.get("error") or task.get("message")
    assert task["best_model"] in task["metrics"]
    assert "decision_tree" in task["metrics"]
    assert "random_forest" in task["metrics"]
    for m in task["metrics"].values():
        assert 0.0 <= m["accuracy"] <= 1.0
        assert 0.0 <= m["f1"] <= 1.0

    # models list
    models = client.get("/api/models").json()
    assert models["count"] >= 2
    assert any(m["name"] == "random_forest" for m in models["models"])

    # experiments
    exp = client.get("/api/experiments").json()
    assert exp["count"] >= 1
    assert exp["comparison"]
    assert any(c.get("is_best") for c in exp["comparison"])

    # export report
    export = client.get("/api/report/export").json()
    assert export["status"] == "ready"
    assert export["bundle"]["metrics_json"] is True
    assert export["bundle"].get("zip_placeholder") is False
    assert export["bundle"].get("zip_path")

    # predict
    pred = client.post(
        "/api/predict",
        json={"samples": [_sample()], "model": task["best_model"]},
    ).json()
    assert pred["count"] == 1
    assert pred["mode"] == "real"
    assert pred["predictions"][0]["label"] in {
        "normal_https",
        "shadowsocks",
        "trojan",
        "vmess",
    }
    assert "confidence" in pred["predictions"][0]
    assert "probabilities" in pred["predictions"][0]


def test_train_fails_without_dataset(client: TestClient):
    r = client.post("/api/train", json={"models": ["decision_tree"]})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "dataset" in detail.lower() or "data" in detail.lower()


def test_settings_persist(client: TestClient):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert "random_seed" in r.json()

    r = client.put(
        "/api/settings",
        json={"random_seed": 7, "n_per_class_default": 120},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["random_seed"] == 7
    assert body["n_per_class_default"] == 120

    again = client.get("/api/settings").json()
    assert again["random_seed"] == 7
    assert again["n_per_class_default"] == 120

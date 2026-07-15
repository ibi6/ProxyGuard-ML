"""Tests for SQLite init and real DatasetService persistence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import FEATURE_COLUMNS, LABELS
from app.db import init_db
from app.main import app
from app.ml.data_generator import generate_synthetic_dataset
from app.services.dataset_service import DatasetService


@pytest.fixture()
def tmp_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


def test_init_db_creates_tables(tmp_path: Path):
    db_path = tmp_path / "proxyguard.db"
    resolved = init_db(db_path)
    assert resolved == db_path
    assert db_path.exists()
    conn = sqlite3.connect(str(db_path))
    try:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()
    assert {"train_tasks", "predict_logs", "settings"} <= names


def test_generate_writes_csv_and_summary(tmp_data_dir: Path):
    svc = DatasetService(data_dir=tmp_data_dir)
    summary = svc.generate(n_per_class=20, seed=42, noise=0.15)

    features = tmp_data_dir / "synthetic" / "features.csv"
    meta = tmp_data_dir / "synthetic" / "meta.json"
    active = tmp_data_dir / "active.json"

    assert features.exists()
    assert meta.exists()
    assert active.exists()

    df = pd.read_csv(features)
    assert len(df) == 80
    assert list(df.columns) == list(FEATURE_COLUMNS) + ["label"]
    assert set(df["label"]) == set(LABELS)

    assert summary["total_samples"] == 80
    assert summary["source"] == "synthetic"
    assert summary["n_per_class"] == 20
    assert summary["seed"] == 42
    assert summary["noise"] == 0.15
    assert summary["class_distribution"] == {k: 20 for k in LABELS}
    assert summary["n_features"] == len(FEATURE_COLUMNS)

    meta_obj = json.loads(meta.read_text(encoding="utf-8"))
    assert meta_obj["source"] == "synthetic"
    assert meta_obj["n_per_class"] == 20

    preview = svc.preview(limit=5)
    assert preview["total"] == 80
    assert len(preview["rows"]) == 5
    assert "label" in preview["columns"]


def test_upload_csv_validates_and_saves(tmp_data_dir: Path):
    svc = DatasetService(data_dir=tmp_data_dir)
    src = generate_synthetic_dataset(n_per_class=5, seed=1)
    csv_bytes = src.to_csv(index=False).encode("utf-8")

    result = svc.upload_csv(csv_bytes, filename="custom.csv")
    assert result["parsed"] is True
    assert result["total_samples"] == 20
    assert result["source"] == "uploaded"

    out = tmp_data_dir / "uploaded" / "features.csv"
    assert out.exists()
    assert svc.summary()["source"] == "uploaded"
    assert svc.summary()["filename"] == "custom.csv"


def test_upload_rejects_missing_columns(tmp_data_dir: Path):
    svc = DatasetService(data_dir=tmp_data_dir)
    bad = b"a,b,label\n1,2,normal_https\n"
    with pytest.raises(ValueError, match="missing feature columns"):
        svc.upload_csv(bad, filename="bad.csv")


def test_api_generate_persists_and_summary():
    """End-to-end via FastAPI: generate creates disk files and summary matches."""
    client = TestClient(app)
    # Use a modest n so tests stay fast
    r = client.post(
        "/api/data/generate",
        json={"n_per_class": 25, "seed": 7, "noise": 0.1},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["total_samples"] == 100
    assert body["source"] == "synthetic"
    assert body["class_distribution"]["vmess"] == 25

    s = client.get("/api/data/summary").json()
    assert s["total_samples"] == 100
    assert set(s["class_distribution"].keys()) == set(LABELS)

    preview = client.get("/api/data/preview?limit=3").json()
    assert preview["total"] == 100
    assert len(preview["rows"]) == 3

    # Disk artifacts under project data/synthetic
    from app.config import DATA_DIR

    assert (DATA_DIR / "synthetic" / "features.csv").exists()
    assert (DATA_DIR / "synthetic" / "meta.json").exists()

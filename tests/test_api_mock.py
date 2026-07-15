"""API smoke tests (real services by default; async train polled)."""

from __future__ import annotations

import time

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_generate_and_summary():
    r = client.post(
        "/api/data/generate",
        json={"n_per_class": 100, "seed": 42, "noise": 0.15},
    )
    assert r.status_code == 200
    s = client.get("/api/data/summary").json()
    assert s["total_samples"] == 400
    assert set(s["class_distribution"].keys()) == {
        "normal_https",
        "shadowsocks",
        "trojan",
        "vmess",
    }


def _poll_task(task_id: str, timeout: float = 180.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        t = client.get(f"/api/train/{task_id}").json()
        last = t
        if t.get("status") in {"success", "failed"}:
            return t
        time.sleep(0.5)
    raise AssertionError(f"timeout waiting for {task_id}: {last}")


def test_train_and_predict():
    client.post("/api/data/generate", json={"n_per_class": 50})
    # Prefer a fast model so smoke stays quick under real training
    r = client.post("/api/train", json={"models": ["decision_tree", "random_forest"]})
    assert r.status_code == 200
    task_id = r.json()["task_id"]
    t = _poll_task(task_id)
    assert t["status"] == "success", t.get("error") or t
    pred = client.post(
        "/api/predict",
        json={
            "samples": [
                {
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
            ]
        },
    ).json()
    assert "predictions" in pred
    assert pred["predictions"][0]["label"] in {
        "normal_https",
        "shadowsocks",
        "trojan",
        "vmess",
    }

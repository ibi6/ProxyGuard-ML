"""API contract regressions for bounded, explicit request payloads."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from app.api.data import GenerateBody
from app.config import FEATURE_COLUMNS
from app.main import app
from app.ml.predict import _samples_to_frame
from fastapi.testclient import TestClient
from starlette.responses import FileResponse


@pytest.fixture
def client() -> TestClient:
    """Create a client for request-validation tests."""
    return TestClient(app)


def test_generate_defaults_match_documented_experiment() -> None:
    """The public API default must match the documented 800-per-class setup."""
    assert GenerateBody().n_per_class == 800


def test_generate_rejects_unknown_fields(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Typos in generation settings must not be silently ignored."""
    monkeypatch.setattr(
        "app.api.data.dataset_service.generate",
        lambda **_kwargs: {"total_samples": 4},
    )

    response = client.post(
        "/api/data/generate",
        json={"n_per_class": 1, "seed": 42, "noise": 0.85, "noize": 0.5},
    )

    assert response.status_code == 422


def test_generate_rejects_boolean_numeric_fields(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boolean JSON values are not valid generation numbers."""
    monkeypatch.setattr(
        "app.api.data.dataset_service.generate",
        lambda **_kwargs: {"total_samples": 4},
    )

    response = client.post(
        "/api/data/generate",
        json={"n_per_class": True, "seed": 42, "noise": 0.85},
    )

    assert response.status_code == 422


def test_train_rejects_unknown_model_before_service(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown model identifiers are schema errors, not worker failures."""
    monkeypatch.setattr("app.api.train.train_service.start", lambda _models: "unexpected")
    monkeypatch.setattr(
        "app.api.train.train_service.get",
        lambda _task_id: {"status": "running"},
    )

    response = client.post("/api/train", json={"models": ["random_forest", "typo"]})

    assert response.status_code == 422


def test_train_deduplicates_models(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate selections must not train or overwrite the same model twice."""
    captured: dict[str, Any] = {}

    def fake_start(models: list[str]) -> str:
        captured["models"] = models
        return "task_contract"

    monkeypatch.setattr("app.api.train.train_service.start", fake_start)
    monkeypatch.setattr(
        "app.api.train.train_service.get",
        lambda _task_id: {"status": "running"},
    )

    response = client.post(
        "/api/train",
        json={"models": ["random_forest", "random_forest", "voting"]},
    )

    assert response.status_code == 200
    assert captured["models"] == ["random_forest", "voting"]


def test_predict_rejects_more_than_500_samples(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single request cannot create an unbounded inference and log workload."""
    monkeypatch.setattr(
        "app.api.predict.predict_service.predict",
        lambda *_args, **_kwargs: {"predictions": [], "count": 0},
    )

    response = client.post("/api/predict", json={"samples": [{} for _ in range(501)]})

    assert response.status_code == 422
    assert all("input" not in item for item in response.json()["detail"])


def test_predict_frame_rejects_non_finite_values() -> None:
    """Inference rejects NaN/Inf just like uploaded training data does."""
    row = {column: 1.0 for column in FEATURE_COLUMNS}
    row["iat_mean"] = float("inf")

    with pytest.raises(ValueError, match="finite|Inf|NaN"):
        _samples_to_frame([row])


def test_predict_schema_rejects_boolean_feature_values(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON booleans must not be coerced to numeric traffic features."""
    row: dict[str, Any] = {column: 1.0 for column in FEATURE_COLUMNS}
    row["iat_mean"] = True
    monkeypatch.setattr(
        "app.api.predict.predict_service.predict",
        lambda *_args, **_kwargs: {"predictions": [], "count": 0},
    )

    response = client.post("/api/predict", json={"samples": [row]})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"unknown_setting": True},
        {"n_per_class_default": 50001},
        {"noise_default": 5.01},
        {"random_seed": -1},
    ],
)
def test_settings_rejects_unknown_or_out_of_range_fields(
    payload: dict[str, Any],
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings use an explicit bounded schema instead of an arbitrary dict."""
    monkeypatch.setattr(
        "app.api.settings.settings_service.update_settings",
        lambda value: value,
    )

    response = client.put("/api/settings", json=payload)

    assert response.status_code == 422


def test_upload_reader_stops_when_size_limit_is_exceeded() -> None:
    """The upload path must enforce the cap while reading, not after read-all."""
    from app.api.data import _read_upload_limited

    class FakeUpload:
        def __init__(self) -> None:
            self.calls: list[int] = []
            self.parts = [b"a" * 8, b"b" * 8, b"c" * 8]

        async def read(self, size: int = -1) -> bytes:
            self.calls.append(size)
            return self.parts.pop(0) if self.parts else b""

    upload = FakeUpload()

    with pytest.raises(ValueError, match="too large"):
        asyncio.run(_read_upload_limited(upload, max_bytes=12, chunk_bytes=8))

    assert upload.calls == [8, 5]


def test_report_download_resolves_against_configured_reports_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report downloads work even when Uvicorn starts outside the repo root."""
    import app.api.experiments as experiments_api

    archive = tmp_path / "experiment_report.zip"
    archive.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    monkeypatch.setattr(experiments_api, "REPORTS_DIR", tmp_path, raising=False)
    monkeypatch.setattr(
        experiments_api.experiment_service,
        "export_report",
        lambda as_zip: {
            "bundle": {"zip_path": "reports/experiment_report.zip"},
            "status": "ready",
        },
    )

    response = experiments_api.export_report(download=True)

    assert isinstance(response, FileResponse)
    assert Path(response.path) == archive


def test_report_generation_uses_write_token_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generating a ZIP is a protected write-like operation."""
    monkeypatch.setattr("app.security.API_TOKEN", "report-secret")
    monkeypatch.setattr(
        "app.api.experiments.experiment_service.export_report",
        lambda as_zip: {"status": "ready", "bundle": {"zip_path": None}},
    )
    client = TestClient(app)

    denied = client.get("/api/report/export")
    allowed = client.get(
        "/api/report/export",
        headers={"X-API-Token": "report-secret"},
    )

    assert denied.status_code == 401
    assert allowed.status_code == 200

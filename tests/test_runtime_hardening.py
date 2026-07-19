"""Runtime, persistence, and response-hardening regressions."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from app.config import DATA_DIR, DB_PATH
from app.db import get_connection, init_db
from app.main import app, unhandled_exception_handler
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient


def test_default_database_is_inside_persisted_data_directory() -> None:
    """Docker's existing data mount must also persist SQLite state."""
    assert Path(DB_PATH).parent == Path(DATA_DIR)


def test_env_int_reports_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid numeric environment values fail with a named configuration error."""
    from app.config import _env_int

    monkeypatch.setenv("PROXYGUARD_TEST_INT", "not-an-int")

    with pytest.raises(RuntimeError, match="PROXYGUARD_TEST_INT.*integer"):
        _env_int("PROXYGUARD_TEST_INT", 10, minimum=1)


def test_token_validation_uses_constant_time_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured API tokens are compared with the standard constant-time helper."""
    import app.security as security

    calls: list[tuple[bytes, bytes]] = []

    def fake_compare(left: bytes, right: bytes) -> bool:
        calls.append((left, right))
        return left == right

    monkeypatch.setattr(security, "API_TOKEN", "sëcret")
    monkeypatch.setattr(security.secrets, "compare_digest", fake_compare)

    asyncio.run(security.require_api_token("sëcret"))

    assert calls == [("sëcret".encode(), "sëcret".encode())]

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(security.require_api_token("wrong"))
    assert exc_info.value.status_code == 401


def test_recover_interrupted_training_tasks(tmp_path: Path) -> None:
    """A process restart must not leave stale tasks permanently running."""
    from app.db import recover_interrupted_tasks

    db_path = tmp_path / "runtime.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO train_tasks (task_id, status, progress, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("task_interrupted", "running", 0.4, "training", "2026-07-16T10:00:00+00:00"),
        )
        conn.commit()

    recovered = recover_interrupted_tasks(db_path)

    assert recovered == 1
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT status, error, message, finished_at FROM train_tasks WHERE task_id = ?",
            ("task_interrupted",),
        ).fetchone()
    assert row is not None
    assert row["status"] == "failed"
    assert "restart" in row["error"].lower()
    assert "中断" in row["message"]
    assert row["finished_at"]


def test_internal_error_response_does_not_expose_exception_type() -> None:
    """Clients receive a stable generic 500 body while logs keep diagnostics."""
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/boom",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 1234),
            "scheme": "http",
        }
    )

    response = asyncio.run(unhandled_exception_handler(request, ValueError("sensitive")))
    body = json.loads(response.body)

    assert response.status_code == 500
    assert body == {"detail": "internal server error"}


def test_security_policy_does_not_trust_unused_tailwind_runtime() -> None:
    """The CSP should not trust the removed Tailwind development CDN."""
    response = TestClient(app).get("/")
    policy = response.headers["content-security-policy"]

    assert "cdn.tailwindcss.com" not in policy
    assert "script-src 'self'" in policy
    assert "'unsafe-inline'" not in policy.split("script-src", 1)[1].split(";", 1)[0]
    assert "object-src 'none'" in policy
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["cache-control"] == "no-store"


def test_versioned_static_assets_receive_long_lived_cache_headers() -> None:
    """Versioned local CSS/JS may be cached without making HTML stale."""
    response = TestClient(app).get("/static/css/app.css?v=0.4.0")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_production_dependencies_exclude_test_only_packages() -> None:
    """Docker runtime installs no pytest/httpx test tooling."""
    runtime = Path("requirements.txt").read_text(encoding="utf-8")
    development = Path("requirements-dev.txt").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "pytest" not in runtime
    assert "httpx" not in runtime
    assert "pytest==8.3.4" in development
    assert "httpx==0.28.1" in development
    assert "pip install -r requirements-dev.txt" in workflow


def test_deployment_artifacts_include_health_persistence_and_proxy_guards() -> None:
    """Compose and Nginx keep the documented production safeguards in source."""
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    nginx = Path("deploy/nginx.conf").read_text(encoding="utf-8")

    assert "name: proxyguard-ml" in compose
    assert "127.0.0.1" in compose
    assert "PROXYGUARD_DB_PATH" in compose
    assert "healthcheck:" in compose
    assert "./data:/app/data" in compose
    assert nginx.count("{") == nginx.count("}")
    assert "client_max_body_size 20m;" in nginx
    assert "limit_req_zone" in nginx
    assert "server proxyguard:8000;" in nginx
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in nginx

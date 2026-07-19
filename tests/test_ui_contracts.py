"""Rendered-page contracts for responsive and accessible console UI."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from app.main import app
from fastapi.testclient import TestClient

PAGES = ("/", "/data", "/train", "/predict", "/experiments", "/settings")


@pytest.fixture
def client() -> TestClient:
    """Return a local page-rendering client."""
    return TestClient(app)


@pytest.mark.parametrize("path", PAGES)
def test_pages_use_local_styles_and_dynamic_health_hooks(
    path: str,
    client: TestClient,
) -> None:
    """Every page avoids Tailwind runtime and probes health dynamically."""
    response = client.get(path)

    assert response.status_code == 200
    assert "cdn.tailwindcss.com" not in response.text
    assert "js-health-pill" in response.text
    assert "js-health-dot" in response.text
    assert "js-health-text" in response.text


@pytest.mark.parametrize("path", PAGES)
def test_pages_mark_current_navigation_and_mobile_menu_state(
    path: str,
    client: TestClient,
) -> None:
    """Assistive technology can identify current navigation and menu state."""
    html = client.get(path).text

    assert html.count('aria-current="page"') == 1
    assert 'id="pg-mobile-toggle"' in html
    assert 'aria-expanded="false"' in html
    assert 'aria-controls="pg-sidebar"' in html


def test_upload_control_has_accessible_label(client: TestClient) -> None:
    """The visually custom upload zone still exposes a real label."""
    html = client.get("/data").text

    assert '<label class="pg-upload-zone" for="data-upload">' in html
    assert 'aria-describedby="data-upload-help"' in html


def test_predict_page_documents_and_bounds_batch_input(client: TestClient) -> None:
    """The browser communicates the same 500-row cap enforced by the API."""
    html = client.get("/predict").text

    assert re.search(r'id="predict-batch"[^>]+maxlength="200000"', html)
    assert "单次最多 500 条" in html


def test_settings_page_uses_documented_default_sample_count(client: TestClient) -> None:
    """The initial settings form matches the 800-per-class experiment contract."""
    html = client.get("/settings").text

    assert re.search(r'id="set-n"[^>]+value="800"', html)


def test_frontend_source_contains_accessible_runtime_behaviors() -> None:
    """Navigation, toasts, visibility polling, and finite values have guards."""
    source = Path("app/static/js/app.js").read_text(encoding="utf-8")

    assert 'setAttribute("aria-expanded"' in source
    assert 'toggleAttribute("inert"' in source
    assert 'event.key === "Escape"' in source
    assert 'setAttribute("role"' in source
    assert "Number.isFinite" in source
    assert "document.hidden" in source


def test_theme_bootstrap_runs_before_styles_without_inline_script(
    client: TestClient,
) -> None:
    """The saved theme is resolved before CSS to prevent a first-paint flash."""
    html = client.get("/").text

    bootstrap = '/static/js/theme-bootstrap.js?v='
    stylesheet = '/static/css/app.css?v='
    assert bootstrap in html
    assert html.index(bootstrap) < html.index(stylesheet)
    assert '<script src="/static/js/theme-bootstrap.js' in html


@pytest.mark.parametrize("path", PAGES)
def test_pages_expose_accessible_three_state_theme_menu(
    path: str,
    client: TestClient,
) -> None:
    """Every page offers system, light, and dark as one accessible preference."""
    html = client.get(path).text

    assert 'id="pg-theme-toggle"' in html
    assert 'aria-haspopup="menu"' in html
    assert 'aria-controls="pg-theme-menu"' in html
    assert 'id="pg-theme-menu"' in html
    assert 'role="menu"' in html
    assert html.count('role="menuitemradio"') == 3
    for theme in ("system", "light", "dark"):
        assert f'data-theme-option="{theme}"' in html


def test_theme_sources_support_persistence_system_changes_and_chart_refresh() -> None:
    """Theme runtime persists the choice and keeps charts in visual sync."""
    bootstrap = Path("app/static/js/theme-bootstrap.js").read_text(encoding="utf-8")
    source = Path("app/static/js/app.js").read_text(encoding="utf-8")

    assert "pg_theme" in bootstrap
    assert "matchMedia" in bootstrap
    assert "dataset.theme" in bootstrap
    assert "pg:themechange" in bootstrap
    assert 'event.key === "Escape"' in source
    assert "pg:themechange" in source
    assert "chart.update" in source


def test_theme_menu_escape_closes_even_when_focus_stays_on_trigger() -> None:
    """Escape is global while the theme menu is open, not limited to menu items."""
    source = Path("app/static/js/app.js").read_text(encoding="utf-8")

    assert 'event.key === "Escape" && !menu.classList.contains("pg-hidden")' in source


def test_dashboard_task_timestamps_do_not_wrap_character_by_character() -> None:
    """The compact dashboard table scrolls instead of collapsing timestamps."""
    source = Path("app/static/js/app.js").read_text(encoding="utf-8")
    styles = Path("app/static/css/app.css").read_text(encoding="utf-8")

    assert 'class="pg-dim pg-nowrap"' in source
    assert ".pg-nowrap" in styles
    assert "white-space: nowrap" in styles

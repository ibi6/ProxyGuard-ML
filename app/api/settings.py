"""Settings API (SQLite-backed; optional USE_MOCK)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.config import USE_MOCK
from app.security import require_api_token
from app.services.mock_store import store
from app.services.settings_service import settings_service

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
def get_settings() -> dict[str, Any]:
    if USE_MOCK:
        return store.get_settings()
    return settings_service.get_settings()


@router.put("/settings", dependencies=[Depends(require_api_token)])
def update_settings(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        if USE_MOCK:
            return store.update_settings(payload)
        return settings_service.update_settings(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

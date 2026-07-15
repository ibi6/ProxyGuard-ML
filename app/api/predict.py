"""Prediction API (real PredictService; optional USE_MOCK)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import USE_MOCK
from app.security import require_api_token
from app.services.mock_store import store
from app.services.predict_service import predict_service

router = APIRouter(prefix="/api", tags=["predict"])


class PredictBody(BaseModel):
    samples: list[dict[str, Any]] = Field(default_factory=list)
    model: str | None = None


@router.post("/predict", dependencies=[Depends(require_api_token)])
def predict(body: PredictBody) -> dict[str, Any]:
    if not body.samples:
        raise HTTPException(status_code=400, detail="samples must not be empty")
    try:
        if USE_MOCK:
            return store.predict(body.samples, model=body.model)
        return predict_service.predict(body.samples, model_name=body.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/predict/stats")
def predict_stats() -> dict[str, Any]:
    """Server-side prediction count for dashboard (not browser localStorage)."""
    if USE_MOCK:
        return {"count": 0, "source": "mock"}
    return {"count": predict_service.count_logs(), "source": "sqlite"}

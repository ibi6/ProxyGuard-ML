"""预测接口。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import PredictRequest
from app.config import USE_MOCK
from app.security import require_api_token
from app.services.mock_store import store
from app.services.predict_service import predict_service

router = APIRouter(prefix="/api", tags=["predict"])


PredictBody = PredictRequest


@router.post("/predict", dependencies=[Depends(require_api_token)])
def predict(body: PredictRequest) -> dict[str, Any]:
    samples = [sample.model_dump() for sample in body.samples]
    try:
        if USE_MOCK:
            return store.predict(samples, model=body.model)
        return predict_service.predict(samples, model_name=body.model)
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

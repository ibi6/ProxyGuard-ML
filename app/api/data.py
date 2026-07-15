"""Data generation / summary / preview API (real DatasetService)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.config import RANDOM_SEED, USE_MOCK
from app.services.dataset_service import dataset_service
from app.services.mock_store import store

router = APIRouter(prefix="/api/data", tags=["data"])


class GenerateBody(BaseModel):
    n_per_class: int = Field(default=1000, ge=1, le=50000)
    seed: int = Field(default=RANDOM_SEED)
    noise: float = Field(default=0.85, ge=0.0, le=5.0)


@router.post("/generate")
def generate_data(body: GenerateBody) -> dict[str, Any]:
    try:
        if USE_MOCK:
            summary = store.generate(
                n_per_class=body.n_per_class,
                seed=body.seed,
                noise=body.noise,
            )
        else:
            summary = dataset_service.generate(
                n_per_class=body.n_per_class,
                seed=body.seed,
                noise=body.noise,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "summary": summary, **summary}


@router.post("/upload")
async def upload_data(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or "upload.csv"
    raw = await file.read()
    if USE_MOCK:
        return store.upload_stub(filename=filename)
    try:
        return dataset_service.upload_csv(raw, filename=filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pandas parse errors etc.
        raise HTTPException(status_code=400, detail=f"invalid CSV: {exc}") from exc


@router.get("/summary")
def data_summary() -> dict[str, Any]:
    if USE_MOCK:
        return store.summary()
    return dataset_service.summary()


@router.get("/preview")
def data_preview(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    if USE_MOCK:
        return store.preview(limit=limit)
    return dataset_service.preview(limit=limit)

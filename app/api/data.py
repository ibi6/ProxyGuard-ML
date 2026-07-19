"""数据相关接口。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.api.schemas import GenerateRequest
from app.config import MAX_UPLOAD_BYTES, USE_MOCK
from app.security import require_api_token
from app.services.dataset_service import dataset_service
from app.services.mock_store import store

router = APIRouter(prefix="/api/data", tags=["data"])


GenerateBody = GenerateRequest


async def _read_upload_limited(
    file: UploadFile,
    *,
    max_bytes: int,
    chunk_bytes: int = 1024 * 1024,
) -> bytes:
    """Read an upload incrementally and stop as soon as the cap is exceeded."""
    if max_bytes < 1 or chunk_bytes < 1:
        raise ValueError("upload size limits must be positive")
    chunks: list[bytes] = []
    total = 0
    while True:
        remaining_probe = min(chunk_bytes, max_bytes - total + 1)
        chunk = await file.read(remaining_probe)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"file too large (max {max_bytes // (1024 * 1024)}MB)")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/generate", dependencies=[Depends(require_api_token)])
def generate_data(body: GenerateRequest) -> dict[str, Any]:
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


@router.post("/upload", dependencies=[Depends(require_api_token)])
async def upload_data(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or "upload.csv"
    if not str(filename).lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="only .csv uploads are allowed")
    try:
        raw = await _read_upload_limited(file, max_bytes=MAX_UPLOAD_BYTES)
    except ValueError as exc:
        raise HTTPException(
            status_code=413,
            detail=str(exc),
        ) from exc
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
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

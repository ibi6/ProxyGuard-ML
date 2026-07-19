"""实验结果接口。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.config import REPORTS_DIR, USE_MOCK
from app.security import require_api_token
from app.services.experiment_service import experiment_service
from app.services.mock_store import store

router = APIRouter(prefix="/api", tags=["experiments"])


@router.get("/experiments")
def list_experiments() -> dict[str, Any]:
    if USE_MOCK:
        return store.experiments()
    return experiment_service.list_metrics()


@router.get("/report/export", dependencies=[Depends(require_api_token)])
def export_report(
    download: bool = Query(default=False, description="If true, return zip file"),
) -> Any:
    if USE_MOCK:
        return store.export_meta()

    meta = experiment_service.export_report(as_zip=True)
    zip_path = (meta.get("bundle") or {}).get("zip_path")
    if download and zip_path:
        from pathlib import Path

        path = Path(zip_path)
        if not path.is_absolute():
            path = Path(REPORTS_DIR) / path.name
        if path.exists():
            return FileResponse(
                path,
                media_type="application/zip",
                filename=path.name,
            )
    return meta

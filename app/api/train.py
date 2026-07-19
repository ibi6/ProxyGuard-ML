"""训练相关接口。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import TrainRequest
from app.config import USE_MOCK
from app.security import require_api_token
from app.services.mock_store import store
from app.services.train_service import train_service

router = APIRouter(prefix="/api", tags=["train"])


TrainBody = TrainRequest


@router.post("/train", dependencies=[Depends(require_api_token)])
def start_train(body: TrainRequest) -> dict[str, Any]:
    try:
        if USE_MOCK:
            task_id = store.start_train(body.models)
            task = store.get_task(task_id)
        else:
            task_id = train_service.start(body.models)
            task = train_service.get(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "task_id": task_id,
        "status": task["status"] if task else "running",
        "task": task,
    }


@router.get("/train")
def list_train_tasks() -> dict[str, Any]:
    if USE_MOCK:
        tasks = store.list_tasks()
    else:
        tasks = train_service.list()
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/train/{task_id}")
def get_train_task(task_id: str) -> dict[str, Any]:
    if USE_MOCK:
        task = store.get_task(task_id)
    else:
        task = train_service.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    return task


@router.post("/train/{task_id}/cancel", dependencies=[Depends(require_api_token)])
def cancel_train(task_id: str) -> dict[str, Any]:
    """取消进行中的训练（当前模型训完后停止）。"""
    if USE_MOCK:
        raise HTTPException(status_code=400, detail="mock mode does not support cancel")
    try:
        return train_service.cancel(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models")
def list_models() -> dict[str, Any]:
    if USE_MOCK:
        return store.list_models()
    return train_service.list_models()

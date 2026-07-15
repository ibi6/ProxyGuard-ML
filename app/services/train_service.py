"""后台训练任务，状态写到 SQLite。"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import (
    MODELS_DIR,
    RANDOM_SEED,
    REPORTS_DIR,
    TEST_RATIO,
    TRAIN_RATIO,
    VAL_RATIO,
)
from app.db import get_connection, init_db
from app.ml.models import MODEL_ZOO, get_model_zoo
from app.ml.train import TrainingCancelled, train_all
from app.services.dataset_service import dataset_service
from app.services.settings_service import settings_service

_ENSEMBLE = frozenset({"voting", "stacking"})


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _json_loads(raw: str | None, default: Any = None) -> Any:
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def _row_to_task(row: Any) -> dict[str, Any]:
    return {
        "task_id": row["task_id"],
        "status": row["status"],
        "models": _json_loads(row["models"], []),
        "config": _json_loads(row["config"], {}),
        "progress": float(row["progress"] or 0),
        "metrics": _json_loads(row["metrics"], {}),
        "best_model": row["best_model"],
        "error": row["error"],
        "message": row["message"],
        "created_at": row["created_at"],
        "finished_at": row["finished_at"],
    }


class TrainService:
    """Start training in a daemon thread; persist task status in SQLite."""

    def __init__(self) -> None:
        init_db()
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self._cancel_flags: dict[str, threading.Event] = {}

    def start(self, models: list[str] | None = None) -> str:
        """Create a running task and train in background. Returns task_id quickly."""
        names = list(models) if models else list(get_model_zoo().keys())
        if not names:
            raise ValueError("models must not be empty")
        zoo = get_model_zoo()
        unknown = [n for n in names if n not in zoo]
        if unknown:
            raise ValueError(f"unknown model(s): {', '.join(unknown)}")

        # Only one training job at a time (avoids joblib / metrics.json races).
        with self._lock:
            alive = [tid for tid, th in self._threads.items() if th.is_alive()]
            if alive:
                raise ValueError(
                    f"another training task is running: {alive[0]}; wait for it to finish"
                )

        df = dataset_service.get_frame()
        if df is None or len(df) == 0:
            raise ValueError("no dataset available; generate or upload data first")

        # Snapshot frame for the worker (avoid mid-train swaps)
        frame = df.copy()
        if len(frame) < 40:
            raise ValueError(
                f"dataset too small ({len(frame)} rows); need >= 40 for stable splits"
            )
        class_counts = frame["label"].value_counts()
        if int(class_counts.min()) < 3:
            raise ValueError(
                "each class needs at least 3 samples for stratified splits; "
                f"distribution={class_counts.to_dict()}"
            )

        summary = dataset_service.summary()
        # Prefer dataset generation seed; else settings page; else config default.
        cfg_seed = settings_service.get_random_seed()
        seed = int(summary.get("seed") if summary.get("seed") is not None else cfg_seed)
        ratios = settings_service.get_split_ratios()

        task_id = f"task_{uuid.uuid4().hex[:12]}"
        created = _utcnow_iso()
        config = {
            "seed": seed,
            "ratios": {"train": ratios[0], "val": ratios[1], "test": ratios[2]},
            "settings_seed": cfg_seed,
            "dataset": {
                "total_samples": int(len(frame)),
                "n_per_class": summary.get("n_per_class"),
                "seed": summary.get("seed"),
                "source": summary.get("source"),
            },
            "note": (
                "decision_tree / random_forest lightly tuned on val; "
                "public metrics are test-set only"
            ),
        }

        cancel_flag = threading.Event()
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO train_tasks (
                    task_id, status, models, config, progress, metrics,
                    best_model, error, message, created_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    "running",
                    _json_dumps(names),
                    _json_dumps(config),
                    0.0,
                    _json_dumps({}),
                    None,
                    None,
                    "training started",
                    created,
                    None,
                ),
            )
            conn.commit()

        thread = threading.Thread(
            target=self._run_train,
            args=(task_id, frame, names, seed, ratios, cancel_flag),
            name=f"train-{task_id}",
            daemon=True,
        )
        with self._lock:
            self._threads[task_id] = thread
            self._cancel_flags[task_id] = cancel_flag
        thread.start()
        return task_id

    def cancel(self, task_id: str) -> dict[str, Any]:
        """Request cancel for a running task (stops between models)."""
        with self._lock:
            flag = self._cancel_flags.get(task_id)
            thread = self._threads.get(task_id)
        if flag is None or thread is None or not thread.is_alive():
            task = self.get(task_id)
            if task is None:
                raise ValueError(f"task not found: {task_id}")
            if task.get("status") != "running":
                raise ValueError(f"task is not running: {task.get('status')}")
            raise ValueError("task worker not found (already finished?)")
        flag.set()
        self._update_task(
            task_id,
            message="cancel requested — will stop after current model",
        )
        return {"task_id": task_id, "status": "cancelling"}

    def _update_task(self, task_id: str, **fields: Any) -> None:
        allowed = {
            "status",
            "progress",
            "metrics",
            "best_model",
            "error",
            "message",
            "finished_at",
            "models",
            "config",
        }
        cols: list[str] = []
        vals: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key in {"metrics", "models", "config"} and not isinstance(value, str):
                value = _json_dumps(value)
            cols.append(f"{key} = ?")
            vals.append(value)
        if not cols:
            return
        vals.append(task_id)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE train_tasks SET {', '.join(cols)} WHERE task_id = ?",
                vals,
            )
            conn.commit()

    def _run_train(
        self,
        task_id: str,
        frame: Any,
        names: list[str],
        seed: int,
        ratios: tuple[float, float, float],
        cancel_flag: threading.Event,
    ) -> None:
        def on_progress(progress: float, message: str) -> None:
            status = "running"
            if cancel_flag.is_set():
                message = f"{message}（正在取消…）"
            self._update_task(
                task_id,
                status=status,
                progress=float(progress),
                message=str(message),
            )

        try:
            self._update_task(
                task_id,
                status="running",
                progress=0.02,
                message="开始训练",
            )
            result = train_all(
                frame,
                model_names=names,
                seed=seed,
                ratios=ratios,
                progress_callback=on_progress,
                should_cancel=cancel_flag.is_set,
            )
            metrics = result.get("metrics") or {}
            best = result.get("best_model")
            self._update_task(
                task_id,
                status="success",
                progress=1.0,
                metrics=metrics,
                best_model=best,
                finished_at=_utcnow_iso(),
                message="训练完成",
                error=None,
            )
        except TrainingCancelled as exc:
            self._update_task(
                task_id,
                status="cancelled",
                progress=1.0,
                error=None,
                message=str(exc) or "已取消",
                finished_at=_utcnow_iso(),
            )
        except Exception as exc:  # noqa: BLE001
            self._update_task(
                task_id,
                status="failed",
                progress=1.0,
                error=str(exc),
                message=f"训练失败: {exc}",
                finished_at=_utcnow_iso(),
            )
        finally:
            with self._lock:
                self._threads.pop(task_id, None)
                self._cancel_flags.pop(task_id, None)

    def get(self, task_id: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM train_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_task(row)

    def list(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM train_tasks ORDER BY created_at DESC"
            ).fetchall()
        return [_row_to_task(r) for r in rows]

    def list_models(self) -> dict[str, Any]:
        """Models trained on disk + metrics from latest successful task / report."""
        metrics_map, best_model, trained_at, task_id = self._latest_metrics_context()
        models: list[dict[str, Any]] = []
        for name in sorted(metrics_map.keys(), key=lambda n: metrics_map[n].get("f1", 0), reverse=True):
            path = MODELS_DIR / f"{name}.joblib"
            models.append(
                {
                    "name": name,
                    "display_name": MODEL_ZOO.get(name, name.replace("_", " ").title()),
                    "status": "ready" if path.exists() else "missing",
                    "metrics": metrics_map[name],
                    "trained_at": trained_at,
                    "task_id": task_id,
                    "is_ensemble": name in _ENSEMBLE,
                    "path": f"models/{name}.joblib" if path.exists() else None,
                }
            )
        # Also surface joblib files without metrics entry
        if MODELS_DIR.exists():
            for path in MODELS_DIR.glob("*.joblib"):
                name = path.stem
                if name in metrics_map:
                    continue
                models.append(
                    {
                        "name": name,
                        "display_name": MODEL_ZOO.get(name, name.replace("_", " ").title()),
                        "status": "ready",
                        "metrics": {},
                        "trained_at": trained_at,
                        "task_id": task_id,
                        "is_ensemble": name in _ENSEMBLE,
                        "path": f"models/{name}.joblib",
                    }
                )
        models.sort(key=lambda m: m.get("metrics", {}).get("f1") or 0, reverse=True)

        available = [
            {
                "name": n,
                "display_name": display,
                "is_ensemble": n in _ENSEMBLE,
                "trained": (MODELS_DIR / f"{n}.joblib").exists(),
            }
            for n, display in get_model_zoo().items()
        ]
        return {
            "models": models,
            "available": available,
            "count": len(models),
            "best_model": best_model,
        }

    def _latest_metrics_context(
        self,
    ) -> tuple[dict[str, dict[str, Any]], str | None, str | None, str | None]:
        # Prefer latest successful train task
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM train_tasks
                WHERE status = 'success'
                ORDER BY finished_at DESC, created_at DESC
                LIMIT 1
                """
            ).fetchone()
        if row is not None:
            metrics = _json_loads(row["metrics"], {}) or {}
            return metrics, row["best_model"], row["finished_at"], row["task_id"]

        # Fallback: reports/metrics.json
        path = REPORTS_DIR / "metrics.json"
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                metrics = payload.get("metrics") or {}
                return metrics, payload.get("best_model"), None, None
            except (OSError, json.JSONDecodeError):
                pass
        return {}, None, None, None


train_service = TrainService()

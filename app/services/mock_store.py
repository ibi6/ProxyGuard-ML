"""内存 Mock，只给前端联调。正式跑实验请 USE_MOCK=false。"""

from __future__ import annotations

import random
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.config import FEATURE_COLUMNS, LABEL_DISPLAY, LABELS, RANDOM_SEED
from app.ml.data_generator import generate_synthetic_dataset

# 和真实实验差不多的量级，别再写成 0.95 那种虚高数
_BASE_METRICS: dict[str, dict[str, float]] = {
    "decision_tree": {"accuracy": 0.600, "f1": 0.604, "precision": 0.609, "recall": 0.600},
    "svm": {"accuracy": 0.750, "f1": 0.748, "precision": 0.747, "recall": 0.750},
    "random_forest": {"accuracy": 0.740, "f1": 0.735, "precision": 0.734, "recall": 0.740},
    "adaboost": {"accuracy": 0.690, "f1": 0.694, "precision": 0.700, "recall": 0.690},
    "xgboost": {"accuracy": 0.727, "f1": 0.725, "precision": 0.723, "recall": 0.727},
    "lightgbm": {"accuracy": 0.725, "f1": 0.723, "precision": 0.722, "recall": 0.725},
    "voting": {"accuracy": 0.752, "f1": 0.752, "precision": 0.752, "recall": 0.752},
    "stacking": {"accuracy": 0.746, "f1": 0.744, "precision": 0.744, "recall": 0.746},
}

_DEFAULT_MODELS = list(_BASE_METRICS.keys())

_DEFAULT_SETTINGS: dict[str, Any] = {
    "random_seed": RANDOM_SEED,
    "train_ratio": 0.70,
    "val_ratio": 0.15,
    "test_ratio": 0.15,
    "n_per_class_default": 1000,
    "noise_default": 0.85,
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _jitter(value: float, rng: random.Random, span: float = 0.008) -> float:
    """Small per-run jitter, clamped near real synthetic-experiment band."""
    v = value + rng.uniform(-span, span)
    return round(min(0.86, max(0.55, v)), 4)


class MockStore:
    """Process-wide in-memory store for stage-1 mock APIs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: list[dict[str, Any]] = []
        self._dataset_meta: dict[str, Any] = {
            "source": "empty",
            "n_per_class": 0,
            "seed": None,
            "noise": None,
            "generated_at": None,
        }
        self._tasks: dict[str, dict[str, Any]] = {}
        self._models: dict[str, dict[str, Any]] = {}
        self._experiments: list[dict[str, Any]] = []
        self._settings: dict[str, Any] = deepcopy(_DEFAULT_SETTINGS)
        self._task_counter = 0

    # ------------------------------------------------------------------ data
    def _summary_unlocked(self) -> dict[str, Any]:
        dist = {label: 0 for label in LABELS}
        for row in self._rows:
            lab = row.get("label")
            if lab in dist:
                dist[lab] += 1
        return {
            "total_samples": len(self._rows),
            "n_features": len(FEATURE_COLUMNS),
            "feature_columns": list(FEATURE_COLUMNS),
            "labels": list(LABELS),
            "label_display": dict(LABEL_DISPLAY),
            "class_distribution": dist,
            "source": self._dataset_meta["source"],
            "n_per_class": self._dataset_meta["n_per_class"],
            "seed": self._dataset_meta["seed"],
            "noise": self._dataset_meta["noise"],
            "generated_at": self._dataset_meta["generated_at"],
        }

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return self._summary_unlocked()

    def preview(self, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit), 200))
        with self._lock:
            rows = self._rows[:limit]
            return {
                "columns": list(FEATURE_COLUMNS) + ["label"],
                "rows": deepcopy(rows),
                "total": len(self._rows),
                "limit": limit,
            }

    def generate(
        self,
        n_per_class: int = 1000,
        seed: int = RANDOM_SEED,
        noise: float = 0.85,
    ) -> dict[str, Any]:
        n_per_class = int(n_per_class)
        if n_per_class < 1:
            raise ValueError("n_per_class must be >= 1")
        df = generate_synthetic_dataset(
            n_per_class=n_per_class, seed=int(seed), noise=float(noise)
        )
        rows = df.to_dict(orient="records")
        with self._lock:
            self._rows = rows
            self._dataset_meta = {
                "source": "synthetic",
                "n_per_class": n_per_class,
                "seed": int(seed),
                "noise": float(noise),
                "generated_at": _utcnow_iso(),
            }
            return self._summary_unlocked()

    def upload_stub(self, filename: str | None = None, n_rows: int | None = None) -> dict[str, Any]:
        """Demo-stage upload acknowledgement (real CSV parse in later stage)."""
        with self._lock:
            # Optionally mark source without requiring real parse
            if n_rows and n_rows > 0 and not self._rows:
                # keep empty but acknowledge
                pass
            self._dataset_meta["source"] = "upload_stub"
            self._dataset_meta["generated_at"] = _utcnow_iso()
            return {
                "status": "accepted",
                "message": "CSV 已校验并保存",
                "filename": filename,
                "parsed": False,
                "summary": self._summary_unlocked(),
            }

    # ----------------------------------------------------------------- train
    def start_train(self, model_names: list[str] | None = None) -> str:
        names = list(model_names) if model_names else list(_DEFAULT_MODELS)
        if not names:
            names = ["random_forest"]
        unknown = [n for n in names if n not in _BASE_METRICS]
        if unknown:
            raise ValueError(f"unknown model(s): {', '.join(unknown)}")

        with self._lock:
            self._task_counter += 1
            task_id = f"task_{self._task_counter:04d}_{uuid.uuid4().hex[:8]}"
            created = _utcnow_iso()
            task: dict[str, Any] = {
                "task_id": task_id,
                "status": "running",
                "models": names,
                "created_at": created,
                "finished_at": None,
                "progress": 0.0,
                "metrics": {},
                "best_model": None,
                "error": None,
                "message": "training started",
            }
            self._tasks[task_id] = task

            # Demo: complete synchronously with realistic fake metrics
            rng = random.Random(hash(task_id) & 0xFFFFFFFF)
            metrics: dict[str, dict[str, float]] = {}
            for name in names:
                base = _BASE_METRICS[name]
                metrics[name] = {
                    "accuracy": _jitter(base["accuracy"], rng),
                    "f1": _jitter(base["f1"], rng),
                    "precision": _jitter(base["precision"], rng),
                    "recall": _jitter(base["recall"], rng),
                }
                # Keep ensemble advantage if both present
                if name in ("voting", "stacking"):
                    for k in metrics[name]:
                        metrics[name][k] = round(min(0.97, metrics[name][k] + 0.01), 4)

            best_model = max(metrics.keys(), key=lambda m: metrics[m]["f1"])
            finished = _utcnow_iso()
            task.update(
                {
                    "status": "success",
                    "progress": 1.0,
                    "metrics": metrics,
                    "best_model": best_model,
                    "finished_at": finished,
                    "message": "training completed (mock)",
                }
            )

            for name, m in metrics.items():
                self._models[name] = {
                    "name": name,
                    "display_name": name.replace("_", " ").title(),
                    "status": "ready",
                    "metrics": m,
                    "trained_at": finished,
                    "task_id": task_id,
                    "is_ensemble": name in ("voting", "stacking"),
                }

            self._experiments.append(
                {
                    "task_id": task_id,
                    "created_at": created,
                    "finished_at": finished,
                    "models": names,
                    "metrics": deepcopy(metrics),
                    "best_model": best_model,
                    "dataset": {
                        "total_samples": len(self._rows),
                        "n_per_class": self._dataset_meta.get("n_per_class"),
                        "seed": self._dataset_meta.get("seed"),
                        "source": self._dataset_meta.get("source"),
                    },
                }
            )
            return task_id

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return deepcopy(task) if task else None

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            items = sorted(
                self._tasks.values(),
                key=lambda t: t.get("created_at") or "",
                reverse=True,
            )
            return deepcopy(items)

    # ----------------------------------------------------------- models / pred
    def list_models(self) -> dict[str, Any]:
        with self._lock:
            models = sorted(
                self._models.values(),
                key=lambda m: m.get("metrics", {}).get("f1", 0),
                reverse=True,
            )
            available = [
                {
                    "name": n,
                    "display_name": n.replace("_", " ").title(),
                    "is_ensemble": n in ("voting", "stacking"),
                    "trained": n in self._models,
                }
                for n in _DEFAULT_MODELS
            ]
            return {
                "models": deepcopy(models),
                "available": available,
                "count": len(models),
            }

    def predict(self, rows: list[dict[str, Any]], model: str | None = None) -> dict[str, Any]:
        if not rows:
            raise ValueError("samples must not be empty")

        with self._lock:
            model_name = model or (
                next(iter(self._models.keys()), None)
                if self._models
                else "random_forest"
            )
            if model_name not in _BASE_METRICS and model_name not in self._models:
                # still allow demo predict with known catalog names
                if model_name not in _BASE_METRICS:
                    raise ValueError(f"unknown model: {model_name}")

            predictions: list[dict[str, Any]] = []
            for i, row in enumerate(rows):
                label = self._heuristic_label(row, seed_offset=i)
                conf = self._confidence_for(label, row)
                proba = self._soft_proba(label, conf)
                predictions.append(
                    {
                        "index": i,
                        "label": label,
                        "display_label": LABEL_DISPLAY.get(label, label),
                        "confidence": conf,
                        "probabilities": proba,
                        "model": model_name,
                    }
                )

            return {
                "predictions": predictions,
                "model": model_name,
                "count": len(predictions),
                "mode": "mock",
            }

    def _heuristic_label(self, row: dict[str, Any], seed_offset: int = 0) -> str:
        """Deterministic-ish label from feature shape (still one of 4 labels)."""
        try:
            pps = float(row.get("packets_per_second", 0) or 0)
            entropy = float(row.get("pkt_size_entropy", 0) or 0)
            iat = float(row.get("iat_mean", 0) or 0)
            burst = float(row.get("iat_burstiness", 0) or 0)
            ratio = float(row.get("byte_up_down_ratio", 0) or 0)
        except (TypeError, ValueError):
            return LABELS[seed_offset % len(LABELS)]

        # Rough separation mirroring synthetic class means
        if pps >= 80 or (entropy >= 4.0 and burst >= 1.8):
            return "vmess"
        if entropy >= 4.2 or (pps >= 50 and iat < 0.025):
            return "shadowsocks"
        if ratio <= 0.45 and iat >= 0.03:
            return "trojan"
        if pps < 40 and 0.03 <= iat <= 0.06:
            return "normal_https"
        # fallback hash
        h = abs(hash((round(pps, 2), round(entropy, 2), seed_offset)))
        return LABELS[h % len(LABELS)]

    def _confidence_for(self, label: str, row: dict[str, Any]) -> float:
        base = 0.78
        try:
            entropy = float(row.get("pkt_size_entropy", 3.0) or 3.0)
            base += min(0.15, abs(entropy - 3.0) * 0.03)
        except (TypeError, ValueError):
            pass
        # slight per-label boost
        boost = {
            "normal_https": 0.04,
            "shadowsocks": 0.05,
            "trojan": 0.03,
            "vmess": 0.06,
        }.get(label, 0.0)
        return round(min(0.99, max(0.55, base + boost)), 4)

    def _soft_proba(self, label: str, confidence: float) -> dict[str, float]:
        remaining = max(0.0, 1.0 - confidence)
        others = [lab for lab in LABELS if lab != label]
        share = remaining / len(others) if others else 0.0
        proba = {lab: round(share, 4) for lab in others}
        proba[label] = round(confidence, 4)
        # renormalize tiny float drift
        total = sum(proba.values()) or 1.0
        return {k: round(v / total, 4) for k, v in proba.items()}

    # -------------------------------------------------------- experiments / io
    def experiments(self) -> dict[str, Any]:
        with self._lock:
            items = deepcopy(self._experiments)
            # latest metrics table for charts
            comparison: list[dict[str, Any]] = []
            if items:
                latest = items[-1]
                for name, m in latest.get("metrics", {}).items():
                    comparison.append(
                        {
                            "model": name,
                            "accuracy": m.get("accuracy"),
                            "f1": m.get("f1"),
                            "precision": m.get("precision"),
                            "recall": m.get("recall"),
                            "is_best": name == latest.get("best_model"),
                        }
                    )
                comparison.sort(key=lambda x: x.get("f1") or 0, reverse=True)
            return {
                "experiments": items,
                "comparison": comparison,
                "count": len(items),
            }

    def export_meta(self) -> dict[str, Any]:
        with self._lock:
            return {
                "format": "json",
                "status": "ready",
                "message": "已生成导出信息",
                "generated_at": _utcnow_iso(),
                "dataset": deepcopy(self._dataset_meta),
                "models": list(self._models.keys()),
                "experiments_count": len(self._experiments),
                "bundle": {
                    "metrics_json": True,
                    "figures": ["confusion_matrix.png", "model_compare.png", "feature_importance.png"],
                    "zip_placeholder": True,
                },
            }

    # --------------------------------------------------------------- settings
    def get_settings(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._settings)

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("settings payload must be an object")
        with self._lock:
            for key, value in payload.items():
                if key in self._settings:
                    self._settings[key] = value
            return deepcopy(self._settings)


# Module-level singleton used by all routers
store = MockStore()

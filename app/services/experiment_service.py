"""实验指标和导出。"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import FIGURES_DIR, REPORTS_DIR
from app.db import get_connection, init_db
from app.services.dataset_service import dataset_service


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_loads(raw: str | None, default: Any = None) -> Any:
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


class ExperimentService:
    """Read train task history + metrics.json; export report bundle."""

    def __init__(self) -> None:
        init_db()

    def list_metrics(self) -> dict[str, Any]:
        """Return experiments list + comparison table (frontend shape)."""
        experiments = self._experiments_from_db()
        if not experiments:
            experiments = self._experiments_from_metrics_file()

        comparison: list[dict[str, Any]] = []
        if experiments:
            latest = experiments[0]  # already newest-first
            for name, m in (latest.get("metrics") or {}).items():
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

        # Extra: full metrics report payload when present
        report = self._load_metrics_file()

        return {
            "experiments": experiments,
            "comparison": comparison,
            "count": len(experiments),
            "report": report,
        }

    def _experiments_from_db(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM train_tasks
                WHERE status = 'success'
                ORDER BY finished_at DESC, created_at DESC
                """
            ).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            config = _json_loads(row["config"], {}) or {}
            items.append(
                {
                    "task_id": row["task_id"],
                    "created_at": row["created_at"],
                    "finished_at": row["finished_at"],
                    "models": _json_loads(row["models"], []),
                    "metrics": _json_loads(row["metrics"], {}),
                    "best_model": row["best_model"],
                    "dataset": config.get("dataset")
                    or {
                        "total_samples": None,
                        "n_per_class": None,
                        "seed": None,
                        "source": None,
                    },
                }
            )
        return items

    def _load_metrics_file(self) -> dict[str, Any] | None:
        path = REPORTS_DIR / "metrics.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _experiments_from_metrics_file(self) -> list[dict[str, Any]]:
        payload = self._load_metrics_file()
        if not payload or not payload.get("metrics"):
            return []
        summary = dataset_service.summary()
        return [
            {
                "task_id": "metrics_json",
                "created_at": None,
                "finished_at": None,
                "models": list((payload.get("metrics") or {}).keys()),
                "metrics": payload.get("metrics") or {},
                "best_model": payload.get("best_model"),
                "dataset": {
                    "total_samples": summary.get("total_samples"),
                    "n_per_class": summary.get("n_per_class"),
                    "seed": summary.get("seed"),
                    "source": summary.get("source"),
                },
            }
        ]

    def list_figures(self) -> list[dict[str, str]]:
        figures: list[dict[str, str]] = []
        if FIGURES_DIR.exists():
            for path in sorted(FIGURES_DIR.glob("*")):
                if path.is_file():
                    figures.append(
                        {
                            "name": path.name,
                            "path": str(path),
                            "relative": f"figures/{path.name}",
                        }
                    )
        return figures

    def export_report(self, as_zip: bool = True) -> dict[str, Any]:
        """Build export metadata; optionally write zip under reports/."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)

        metrics_path = REPORTS_DIR / "metrics.json"
        figures = self.list_figures()
        summary = dataset_service.summary()
        experiments = self.list_metrics()

        models: list[str] = []
        if experiments.get("comparison"):
            models = [c["model"] for c in experiments["comparison"]]
        elif metrics_path.exists():
            payload = self._load_metrics_file() or {}
            models = list((payload.get("metrics") or {}).keys())

        zip_path: Path | None = None
        zip_placeholder = True
        if as_zip:
            zip_path = REPORTS_DIR / "experiment_report.zip"
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                if metrics_path.exists():
                    zf.write(metrics_path, arcname="metrics.json")
                for fig in figures:
                    p = Path(fig["path"])
                    if p.exists():
                        zf.write(p, arcname=f"figures/{p.name}")
                # Include a small manifest
                manifest = {
                    "generated_at": _utcnow_iso(),
                    "models": models,
                    "figures": [f["name"] for f in figures],
                    "dataset": {
                        "total_samples": summary.get("total_samples"),
                        "source": summary.get("source"),
                        "n_per_class": summary.get("n_per_class"),
                        "seed": summary.get("seed"),
                    },
                }
                zf.writestr(
                    "manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                )
            zip_placeholder = False

        return {
            "format": "zip" if zip_path and zip_path.exists() else "json",
            "status": "ready",
            "message": "实验报告已生成",
            "generated_at": _utcnow_iso(),
            "dataset": {
                "source": summary.get("source"),
                "n_per_class": summary.get("n_per_class"),
                "seed": summary.get("seed"),
                "noise": summary.get("noise"),
                "generated_at": summary.get("generated_at"),
                "total_samples": summary.get("total_samples"),
            },
            "models": models,
            "experiments_count": experiments.get("count", 0),
            "bundle": {
                "metrics_json": metrics_path.exists(),
                "metrics_path": "reports/metrics.json" if metrics_path.exists() else None,
                "figures": [f["name"] for f in figures],
                "figure_paths": [f"reports/figures/{f['name']}" for f in figures],
                "zip_path": (
                    "reports/experiment_report.zip"
                    if zip_path and zip_path.exists()
                    else None
                ),
                "zip_placeholder": zip_placeholder,
            },
            "comparison": experiments.get("comparison") or [],
        }


experiment_service = ExperimentService()

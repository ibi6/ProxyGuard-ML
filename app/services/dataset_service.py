"""Persist synthetic / uploaded feature datasets and serve summary/preview."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

from app.config import (
    DATA_DIR,
    FEATURE_COLUMNS,
    LABEL_DISPLAY,
    LABELS,
    RANDOM_SEED,
)
from app.ml.data_generator import generate_synthetic_dataset
from app.ml.features import validate_feature_frame

SYNTHETIC_DIR = DATA_DIR / "synthetic"
UPLOADED_DIR = DATA_DIR / "uploaded"
ACTIVE_META_PATH = DATA_DIR / "active.json"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _empty_meta() -> dict[str, Any]:
    return {
        "source": "empty",
        "n_per_class": 0,
        "seed": None,
        "noise": None,
        "generated_at": None,
        "filename": None,
        "path": None,
    }


class DatasetService:
    """Generate / upload / summarize flow-feature datasets on disk."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else Path(DATA_DIR)
        self.synthetic_dir = self.data_dir / "synthetic"
        self.uploaded_dir = self.data_dir / "uploaded"
        self.active_meta_path = self.data_dir / "active.json"
        self.synthetic_dir.mkdir(parents=True, exist_ok=True)
        self.uploaded_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._df: pd.DataFrame | None = None
        self._meta: dict[str, Any] = _empty_meta()
        self._load_active_unlocked()

    # ------------------------------------------------------------------ paths
    def _features_path(self, source: str) -> Path:
        if source == "synthetic":
            return self.synthetic_dir / "features.csv"
        if source == "uploaded":
            return self.uploaded_dir / "features.csv"
        raise ValueError(f"unknown dataset source: {source}")

    def _meta_path(self, source: str) -> Path:
        if source == "synthetic":
            return self.synthetic_dir / "meta.json"
        if source == "uploaded":
            return self.uploaded_dir / "meta.json"
        raise ValueError(f"unknown dataset source: {source}")

    # --------------------------------------------------------------- persistence
    def _write_active(self, meta: dict[str, Any]) -> None:
        payload = {
            "source": meta.get("source"),
            "path": meta.get("path"),
            "generated_at": meta.get("generated_at"),
        }
        self.active_meta_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_frame(self, df: pd.DataFrame, source: str, meta: dict[str, Any]) -> dict[str, Any]:
        features_path = self._features_path(source)
        meta_path = self._meta_path(source)
        features_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(features_path, index=False)
        meta = dict(meta)
        meta["source"] = source
        # Store portable relative path when under project data/
        try:
            meta["path"] = str(features_path.relative_to(self.data_dir.parent)).replace(
                "\\", "/"
            )
        except ValueError:
            meta["path"] = features_path.name
        meta["path_absolute"] = str(features_path)  # local-only convenience; not for publish
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_active(meta)
        self._df = df.reset_index(drop=True)
        self._meta = meta
        return self._summary_unlocked()

    def _load_active_unlocked(self) -> None:
        """Best-effort restore of last active dataset from disk."""
        candidates: list[Path] = []
        if self.active_meta_path.exists():
            try:
                active = json.loads(self.active_meta_path.read_text(encoding="utf-8"))
                source = active.get("source")
                if source in ("synthetic", "uploaded"):
                    candidates.append(self._features_path(source))
            except (OSError, json.JSONDecodeError, ValueError):
                pass
        # Fallbacks: synthetic then uploaded
        candidates.extend(
            [
                self.synthetic_dir / "features.csv",
                self.uploaded_dir / "features.csv",
            ]
        )
        seen: set[Path] = set()
        for path in candidates:
            path = Path(path)
            if path in seen or not path.exists():
                continue
            seen.add(path)
            try:
                df = pd.read_csv(path)
                df = validate_feature_frame(df)
            except (OSError, ValueError, pd.errors.ParserError):
                continue
            source = "uploaded" if "uploaded" in path.parts else "synthetic"
            meta_path = self._meta_path(source)
            meta = _empty_meta()
            if meta_path.exists():
                try:
                    meta = {**meta, **json.loads(meta_path.read_text(encoding="utf-8"))}
                except (OSError, json.JSONDecodeError):
                    pass
            meta["source"] = source
            meta["path"] = str(path)
            self._df = df
            self._meta = meta
            return
        self._df = None
        self._meta = _empty_meta()

    # ------------------------------------------------------------------ summary
    def _summary_unlocked(self) -> dict[str, Any]:
        dist = {label: 0 for label in LABELS}
        total = 0
        if self._df is not None and len(self._df):
            counts = self._df["label"].value_counts().to_dict()
            for label in LABELS:
                dist[label] = int(counts.get(label, 0))
            total = int(len(self._df))
        return {
            "total_samples": total,
            "n_features": len(FEATURE_COLUMNS),
            "feature_columns": list(FEATURE_COLUMNS),
            "labels": list(LABELS),
            "label_display": dict(LABEL_DISPLAY),
            "class_distribution": dist,
            "source": self._meta.get("source") or "empty",
            "n_per_class": self._meta.get("n_per_class") or 0,
            "seed": self._meta.get("seed"),
            "noise": self._meta.get("noise"),
            "generated_at": self._meta.get("generated_at"),
            "filename": self._meta.get("filename"),
        }

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return self._summary_unlocked()

    def preview(self, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit), 200))
        with self._lock:
            if self._df is None or self._df.empty:
                return {
                    "columns": list(FEATURE_COLUMNS) + ["label"],
                    "rows": [],
                    "total": 0,
                    "limit": limit,
                }
            head = self._df.head(limit)
            rows = head.to_dict(orient="records")
            # JSON-friendly floats
            for row in rows:
                for k, v in list(row.items()):
                    if k == "label":
                        continue
                    try:
                        row[k] = float(v)
                    except (TypeError, ValueError):
                        pass
            return {
                "columns": list(FEATURE_COLUMNS) + ["label"],
                "rows": rows,
                "total": int(len(self._df)),
                "limit": limit,
            }

    def get_frame(self) -> pd.DataFrame | None:
        """Return a copy of the active feature frame, or None if empty."""
        with self._lock:
            if self._df is None:
                return None
            return self._df.copy()

    # ---------------------------------------------------------------- generate
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
            n_per_class=n_per_class,
            seed=int(seed),
            noise=float(noise),
        )
        df = validate_feature_frame(df)
        meta = {
            "source": "synthetic",
            "n_per_class": n_per_class,
            "seed": int(seed),
            "noise": float(noise),
            "generated_at": _utcnow_iso(),
            "filename": "features.csv",
            "total_samples": int(len(df)),
        }
        with self._lock:
            return self._save_frame(df, "synthetic", meta)

    # ------------------------------------------------------------------ upload
    def upload_csv(
        self,
        file_path_or_bytes: str | Path | bytes | BinaryIO,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Validate a CSV feature frame and persist under data/uploaded/."""
        if isinstance(file_path_or_bytes, (str, Path)):
            path = Path(file_path_or_bytes)
            df = pd.read_csv(path)
            name = filename or path.name
        elif isinstance(file_path_or_bytes, (bytes, bytearray)):
            df = pd.read_csv(BytesIO(file_path_or_bytes))
            name = filename or "upload.csv"
        else:
            # file-like
            raw = file_path_or_bytes.read()
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            df = pd.read_csv(BytesIO(raw))
            name = filename or getattr(file_path_or_bytes, "name", None) or "upload.csv"

        df = validate_feature_frame(df)
        # n_per_class is approximate for unbalanced uploads
        counts = df["label"].value_counts()
        n_per = int(counts.min()) if len(counts) else 0
        meta = {
            "source": "uploaded",
            "n_per_class": n_per,
            "seed": None,
            "noise": None,
            "generated_at": _utcnow_iso(),
            "filename": name,
            "total_samples": int(len(df)),
        }
        with self._lock:
            summary = self._save_frame(df, "uploaded", meta)
        return {
            "status": "ok",
            "message": f"已解析并保存 {len(df)} 条样本",
            "filename": name,
            "parsed": True,
            "summary": summary,
            **summary,
        }


# Module-level singleton used by data API
dataset_service = DatasetService()

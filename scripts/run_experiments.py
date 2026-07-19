#!/usr/bin/env python
"""Offline experiment runner: generate data, train models, export paper figures.

Usage (from repo root, with venv activated)::

    python scripts/run_experiments.py --n-per-class 800 --seed 42 --noise 0.85

Verification (smaller sample)::

    python scripts/run_experiments.py --n-per-class 200 --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path when invoked as a script
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import FIGURES_DIR, LABELS, RANDOM_SEED, REPORTS_DIR  # noqa: E402
from app.ml.data_generator import generate_synthetic_dataset  # noqa: E402
from app.ml.models import get_model_zoo  # noqa: E402
from app.ml.train import train_all  # noqa: E402


def _parse_models(raw: str | None) -> list[str] | None:
    if raw is None or raw.strip() == "" or raw.strip().lower() == "all":
        return None
    names = [p.strip() for p in raw.split(",") if p.strip()]
    return names or None


def _format_metrics_table(metrics_map: dict[str, dict[str, Any]], best: str | None) -> str:
    headers = ("Model", "Accuracy", "Precision", "Recall", "F1", "Best")
    rows: list[tuple[str, str, str, str, str, str]] = []
    ordered = sorted(
        metrics_map.items(),
        key=lambda kv: float(kv[1].get("f1") or 0.0),
        reverse=True,
    )
    for name, m in ordered:
        rows.append(
            (
                name,
                f"{float(m.get('accuracy', 0)):.4f}",
                f"{float(m.get('precision', 0)):.4f}",
                f"{float(m.get('recall', 0)):.4f}",
                f"{float(m.get('f1', 0)):.4f}",
                "*" if name == best else "",
            )
        )

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(row: Sequence[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    sep = "-+-".join("-" * w for w in widths)
    lines = [fmt(headers), sep]
    lines.extend(fmt(r) for r in rows)
    return "\n".join(lines)


def run_experiments(
    n_per_class: int = 800,
    seed: int = RANDOM_SEED,
    noise: float = 0.85,
    models: list[str] | None = None,
) -> dict[str, Any]:
    """Generate synthetic data, train models, write reports/metrics + figures."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Generating synthetic dataset (n_per_class={n_per_class}, seed={seed}, noise={noise})")
    df = generate_synthetic_dataset(n_per_class=n_per_class, seed=seed, noise=noise)
    print(f"      rows={len(df)}, labels={list(LABELS)}")

    model_names = models if models is not None else list(get_model_zoo().keys())
    print(f"[2/3] Training models: {', '.join(model_names)}")
    result = train_all(df, model_names=model_names, seed=seed)

    print("[3/3] Metrics table")
    table = _format_metrics_table(result.get("metrics") or {}, result.get("best_model"))
    print(table)
    print()
    print(f"best_model = {result.get('best_model')}")
    print(f"metrics    = {REPORTS_DIR / 'metrics.json'}")

    figures = result.get("figures") or {}
    print("figures:")
    for key, path in figures.items():
        status = path if path else "(missing)"
        print(f"  - {key}: {status}")

    # Explicit required checklist for paper export
    required = [
        FIGURES_DIR / "model_accuracy_comparison.png",
        FIGURES_DIR / "model_f1_comparison.png",
        FIGURES_DIR / f"confusion_matrix_{result.get('best_model')}.png",
        FIGURES_DIR / "feature_importance.png",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print("WARNING: missing required figures:")
        for p in missing:
            print(f"  - {p}")
    else:
        print("All required paper figures are present under reports/figures/.")

    # Lightweight experiment summary next to metrics.json
    summary_path = REPORTS_DIR / "experiment_summary.json"
    summary = {
        "n_per_class": n_per_class,
        "seed": seed,
        "noise": noise,
        "n_samples": int(len(df)),
        "models": model_names,
        "best_model": result.get("best_model"),
        "metrics": result.get("metrics"),
        "figures": figures,
        "required_figures_ok": len(missing) == 0,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"summary   = {summary_path}")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline ML experiment runner for paper-ready figures.",
    )
    parser.add_argument(
        "--n-per-class",
        type=int,
        default=800,
        help="samples per traffic class (default: 800)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOM_SEED,
        help=f"random seed (default: {RANDOM_SEED})",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=0.85,
        help="synthetic feature noise scale (default: 0.85)",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="all",
        help="comma-separated model names, or 'all' (default: all)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.n_per_class < 1:
        parser.error("--n-per-class must be >= 1")
    if args.noise < 0:
        parser.error("--noise must be >= 0")

    models = _parse_models(args.models)
    if models is not None:
        zoo = get_model_zoo()
        unknown = [n for n in models if n not in zoo]
        if unknown:
            parser.error(f"unknown model(s): {', '.join(unknown)}")

    run_experiments(
        n_per_class=args.n_per_class,
        seed=args.seed,
        noise=args.noise,
        models=models,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

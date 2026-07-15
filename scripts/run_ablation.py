"""Ablation experiments for thesis: noise & sample size sweeps."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ml.data_generator import generate_synthetic_dataset  # noqa: E402
from app.ml.train import train_all  # noqa: E402

OUT = ROOT / "reports" / "ablation_results.json"
MODELS = [
    "decision_tree",
    "svm",
    "random_forest",
    "adaboost",
    "xgboost",
    "lightgbm",
    "voting",
    "stacking",
]


def run_one(n_per_class: int, noise: float, seed: int = 42) -> dict:
    df = generate_synthetic_dataset(n_per_class=n_per_class, seed=seed, noise=noise)
    result = train_all(df, MODELS, seed=seed)
    metrics = {
        name: {
            "accuracy": round(float(m["accuracy"]), 4),
            "f1": round(float(m["f1"]), 4),
        }
        for name, m in result["metrics"].items()
    }
    return {
        "n_per_class": n_per_class,
        "n_samples": n_per_class * 4,
        "noise": noise,
        "seed": seed,
        "best_model": result["best_model"],
        "best_f1": round(float(result["metrics"][result["best_model"]]["f1"]), 4),
        "metrics": metrics,
    }


def main():
    # Keep runtime reasonable for laptop while producing thesis-usable tables
    noise_grid = [0.55, 0.85, 1.15]
    size_grid = [300, 500, 800]
    fixed_noise_for_size = 0.85
    fixed_size_for_noise = 500

    noise_rows = []
    for noise in noise_grid:
        print(f"[noise sweep] n_per_class={fixed_size_for_noise}, noise={noise}")
        row = run_one(fixed_size_for_noise, noise)
        noise_rows.append(row)
        print("  best", row["best_model"], row["best_f1"])

    size_rows = []
    for n in size_grid:
        print(f"[size sweep] n_per_class={n}, noise={fixed_noise_for_size}")
        row = run_one(n, fixed_noise_for_size)
        size_rows.append(row)
        print("  best", row["best_model"], row["best_f1"])

    payload = {
        "noise_sweep": {
            "fixed_n_per_class": fixed_size_for_noise,
            "rows": noise_rows,
        },
        "size_sweep": {
            "fixed_noise": fixed_noise_for_size,
            "rows": size_rows,
        },
        "main_formal": {
            "n_per_class": 800,
            "noise": 0.85,
            "note": "formal metrics remain in reports/experiment_summary.json",
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

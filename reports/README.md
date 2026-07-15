# Experiment Reports

This directory holds training metrics and paper-ready figures produced by the
offline runner and by Web training (`train_all`).

## How to generate

From the project root (venv activated):

```powershell
python scripts/run_experiments.py --n-per-class 1000 --seed 42
```

Faster smoke run:

```powershell
python scripts/run_experiments.py --n-per-class 200 --seed 42
```

Optional flags:

- `--models random_forest,voting,stacking` — train a subset
- `--noise 0.15` — synthetic feature noise scale

Web training also writes the same artifacts when a train task completes
successfully (metrics + figures under this folder).

## Artifacts

| Path | Description |
|------|-------------|
| `metrics.json` | Full training payload: per-model accuracy/precision/recall/F1, confusion matrices, feature importances, best model, split sizes, figure paths |
| `experiment_summary.json` | Compact offline-run summary (written by `run_experiments.py`) |
| `experiment_report.zip` | Optional Web export bundle (metrics + figures + manifest) |
| `figures/` | PNG charts for thesis / slides |

### Required paper figures (`figures/`)

| File | Content |
|------|---------|
| `model_accuracy_comparison.png` | Bar chart of accuracy across trained models |
| `model_f1_comparison.png` | Bar chart of macro-F1 across trained models |
| `confusion_matrix_{best_model}.png` | Confusion matrix for the best model (by F1) |
| `feature_importance.png` | Top feature importances (preferred: best model / tree ensemble) |

Additional per-model confusion matrices may also appear as
`confusion_matrix_<model_name>.png` for Web experiment pages.

Chart titles are in **English** to avoid Chinese font issues on headless
Windows; captions in thesis docs can be Chinese.

## Notes

- Figures use matplotlib `Agg` backend (no GUI required).
- Feature importance is available for tree / boosting / linear models; pure
  soft-voting ensembles may fall back to another model’s importances.
- Metrics are computed on the held-out test split (`test=0.15` by default).

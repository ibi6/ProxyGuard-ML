"""算指标，画对比图。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from app.config import FIGURES_DIR, LABELS, REPORTS_DIR

# Paper figure style (English titles — avoid CJK font issues on Windows).
_FIG_DPI = 150
_PALETTE = {
    "bar": "#2563eb",
    "bar_edge": "#1e3a8a",
    "accent": "#0ea5e9",
    "grid": "#e2e8f0",
    "text": "#0f172a",
}


def evaluate_model(
    model: Any,
    X_test: Any,
    y_test: Any,
    labels: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Compute accuracy / precision / recall / F1 (macro) + confusion matrix.

    Returns a JSON-serializable dict. Confusion matrix is a nested list ordered
    by ``labels`` (defaults to project LABELS).
    """
    label_list = list(labels) if labels is not None else list(LABELS)
    y_pred = model.predict(X_test)

    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(
            precision_score(
                y_test,
                y_pred,
                labels=label_list,
                average="macro",
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_test,
                y_pred,
                labels=label_list,
                average="macro",
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                y_test,
                y_pred,
                labels=label_list,
                average="macro",
                zero_division=0,
            )
        ),
        "confusion_matrix": confusion_matrix(
            y_test, y_pred, labels=label_list
        ).tolist(),
        "labels": list(label_list),
    }
    return metrics


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)!r} is not JSON serializable")


def save_metrics_report(
    payload: dict[str, Any],
    path: Path | None = None,
) -> Path:
    """Write metrics payload to reports/metrics.json (or custom path)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = path or (REPORTS_DIR / "metrics.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    return out


def _matplotlib_ready() -> tuple[Any, Any, Any] | None:
    """Import matplotlib (Agg) + seaborn; return (plt, sns, matplotlib) or None."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns
    except Exception:  # pragma: no cover
        return None
    return plt, sns, matplotlib


def _style_axes(ax: Any) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=_PALETTE["text"])
    ax.yaxis.grid(True, color=_PALETTE["grid"], linestyle="--", linewidth=0.8)
    ax.set_axisbelow(True)


def try_save_confusion_figure(
    cm: Sequence[Sequence[float]] | np.ndarray,
    labels: Sequence[str],
    model_name: str,
    out_dir: Path | None = None,
) -> Path | None:
    """Save confusion matrix PNG for one model."""
    mods = _matplotlib_ready()
    if mods is None:
        return None
    plt, sns, _ = mods

    target_dir = out_dir or FIGURES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"confusion_matrix_{model_name}.png"

    arr = np.asarray(cm)
    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    sns.heatmap(
        arr,
        annot=True,
        fmt="d" if np.issubdtype(arr.dtype, np.integer) else ".0f",
        cmap="Blues",
        xticklabels=list(labels),
        yticklabels=list(labels),
        ax=ax,
        cbar_kws={"shrink": 0.8},
        linewidths=0.4,
        linecolor="#cbd5e1",
    )
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_title(f"Confusion Matrix — {model_name}")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.setp(ax.get_yticklabels(), rotation=0)
    fig.tight_layout()
    fig.savefig(path, dpi=_FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def save_metric_bar_chart(
    metrics_map: Mapping[str, Mapping[str, Any]],
    metric_key: str,
    title: str,
    ylabel: str,
    filename: str,
    out_dir: Path | None = None,
) -> Path | None:
    """Bar chart of one scalar metric across models (sorted by value desc)."""
    mods = _matplotlib_ready()
    if mods is None or not metrics_map:
        return None
    plt, _, _ = mods

    rows = [
        (name, float(m.get(metric_key, 0.0) or 0.0))
        for name, m in metrics_map.items()
    ]
    rows.sort(key=lambda x: x[1], reverse=True)
    names = [r[0] for r in rows]
    values = [r[1] for r in rows]

    target_dir = out_dir or FIGURES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / filename

    fig, ax = plt.subplots(figsize=(max(8.0, 0.9 * len(names) + 2), 5.2))
    x = np.arange(len(names))
    bars = ax.bar(
        x,
        values,
        color=_PALETTE["bar"],
        edgecolor=_PALETTE["bar_edge"],
        linewidth=0.8,
        width=0.72,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=25, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(0.0, min(1.05, max(values + [0.0]) * 1.12 + 0.02))
    _style_axes(ax)

    for bar, val in zip(bars, values):
        ax.annotate(
            f"{val:.3f}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color=_PALETTE["text"],
        )

    fig.tight_layout()
    fig.savefig(path, dpi=_FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def save_accuracy_comparison_figure(
    metrics_map: Mapping[str, Mapping[str, Any]],
    out_dir: Path | None = None,
) -> Path | None:
    return save_metric_bar_chart(
        metrics_map,
        metric_key="accuracy",
        title="Model Accuracy Comparison",
        ylabel="Accuracy",
        filename="model_accuracy_comparison.png",
        out_dir=out_dir,
    )


def save_f1_comparison_figure(
    metrics_map: Mapping[str, Mapping[str, Any]],
    out_dir: Path | None = None,
) -> Path | None:
    return save_metric_bar_chart(
        metrics_map,
        metric_key="f1",
        title="Model Macro-F1 Comparison",
        ylabel="Macro-F1",
        filename="model_f1_comparison.png",
        out_dir=out_dir,
    )


def save_feature_importance_figure(
    feature_importances: Mapping[str, Mapping[str, float]] | Mapping[str, float],
    *,
    preferred_model: str | None = None,
    top_k: int = 15,
    out_dir: Path | None = None,
) -> Path | None:
    """Horizontal bar chart of feature importances.

    Accepts either:
      - {feature: weight} for a single model, or
      - {model_name: {feature: weight}} and picks preferred / first non-empty.
    """
    mods = _matplotlib_ready()
    if mods is None:
        return None
    plt, _, _ = mods

    fi: Mapping[str, float] | None = None
    source_model = preferred_model or "model"

    if feature_importances and all(
        isinstance(v, (int, float, np.floating)) for v in feature_importances.values()
    ):
        fi = {str(k): float(v) for k, v in feature_importances.items()}  # type: ignore[arg-type]
    else:
        nested = feature_importances  # type: ignore[assignment]
        candidates: list[str] = []
        if preferred_model and preferred_model in nested:
            candidates.append(preferred_model)
        # Prefer tree-like models with non-empty FI
        for name in (
            "random_forest",
            "xgboost",
            "lightgbm",
            "decision_tree",
            "adaboost",
        ):
            if name not in candidates and name in nested:
                candidates.append(name)
        candidates.extend([n for n in nested.keys() if n not in candidates])
        for name in candidates:
            payload = nested.get(name) or {}
            if isinstance(payload, Mapping) and payload:
                fi = {str(k): float(v) for k, v in payload.items()}
                source_model = name
                break

    if not fi:
        return None

    items = sorted(fi.items(), key=lambda kv: kv[1], reverse=True)[: max(1, top_k)]
    items = list(reversed(items))  # smallest at bottom for horizontal bars
    names = [k for k, _ in items]
    values = [v for _, v in items]

    target_dir = out_dir or FIGURES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "feature_importance.png"

    fig_h = max(4.5, 0.38 * len(names) + 1.5)
    fig, ax = plt.subplots(figsize=(8.5, fig_h))
    y = np.arange(len(names))
    ax.barh(
        y,
        values,
        color=_PALETTE["accent"],
        edgecolor="#0369a1",
        linewidth=0.6,
        height=0.7,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Normalized importance")
    ax.set_title(f"Feature Importance — {source_model}")
    _style_axes(ax)
    ax.xaxis.grid(True, color=_PALETTE["grid"], linestyle="--", linewidth=0.8)
    ax.yaxis.grid(False)

    for yi, val in zip(y, values):
        ax.annotate(
            f"{val:.3f}",
            xy=(val, yi),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=_PALETTE["text"],
        )

    fig.tight_layout()
    fig.savefig(path, dpi=_FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def export_experiment_figures(
    result: Mapping[str, Any],
    out_dir: Path | None = None,
) -> dict[str, str | None]:
    """Export all paper-required PNGs from a train_all / metrics payload.

    Required artifacts:
      - model_accuracy_comparison.png
      - model_f1_comparison.png
      - confusion_matrix_{best_model}.png
      - feature_importance.png
    """
    target_dir = out_dir or FIGURES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    metrics_map = result.get("metrics") or {}
    best_model = result.get("best_model")
    if not best_model and metrics_map:
        best_model = max(
            metrics_map.keys(),
            key=lambda n: float((metrics_map[n] or {}).get("f1") or 0.0),
        )

    labels = list(result.get("labels") or LABELS)
    cm_map = result.get("confusion_matrices") or {}
    fi_map = result.get("feature_importances") or {}

    paths: dict[str, str | None] = {
        "model_accuracy_comparison": None,
        "model_f1_comparison": None,
        "confusion_matrix_best": None,
        "feature_importance": None,
    }

    def _rel(p: Path | None) -> str | None:
        if p is None:
            return None
        # Prefer repo-relative style path for portable metrics.json
        try:
            return f"reports/figures/{p.name}"
        except Exception:  # noqa: BLE001
            return p.name

    p_acc = save_accuracy_comparison_figure(metrics_map, out_dir=target_dir)
    paths["model_accuracy_comparison"] = _rel(p_acc)

    p_f1 = save_f1_comparison_figure(metrics_map, out_dir=target_dir)
    paths["model_f1_comparison"] = _rel(p_f1)

    if best_model and best_model in cm_map:
        p_cm = try_save_confusion_figure(
            cm_map[best_model],
            labels,
            str(best_model),
            out_dir=target_dir,
        )
        paths["confusion_matrix_best"] = _rel(p_cm)
    elif best_model:
        # Still write empty-looking figure only if CM missing — skip
        paths["confusion_matrix_best"] = None

    # Also refresh CMs for every model when available (web export convenience)
    for name, cm in cm_map.items():
        try_save_confusion_figure(cm, labels, str(name), out_dir=target_dir)

    p_fi = save_feature_importance_figure(
        fi_map,
        preferred_model=str(best_model) if best_model else None,
        out_dir=target_dir,
    )
    paths["feature_importance"] = _rel(p_fi)

    return paths

"""合成流特征数据。固定 seed 可以复现。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.config import FEATURE_COLUMNS, LABELS, RANDOM_SEED

# 各类别特征均值。HTTPS 和 Trojan 故意设得近一点，避免准确率虚高到 1.0
_CLASS_MEANS: dict[str, dict[str, float]] = {
    "normal_https": {
        "pkt_len_mean": 560.0,
        "pkt_len_std": 190.0,
        "pkt_len_min": 55.0,
        "pkt_len_max": 1420.0,
        "pkt_len_p25": 360.0,
        "pkt_len_p75": 860.0,
        "iat_mean": 0.040,
        "iat_std": 0.022,
        "iat_burstiness": 1.05,
        "uplink_pkt_ratio": 0.47,
        "byte_up_down_ratio": 0.70,
        "duration": 7.5,
        "total_packets": 260.0,
        "total_bytes": 145000.0,
        "packets_per_second": 36.0,
        "pkt_size_entropy": 3.5,
        "iat_entropy": 3.0,
    },
    "shadowsocks": {
        "pkt_len_mean": 420.0,
        "pkt_len_std": 150.0,
        "pkt_len_min": 45.0,
        "pkt_len_max": 1200.0,
        "pkt_len_p25": 260.0,
        "pkt_len_p75": 620.0,
        "iat_mean": 0.028,
        "iat_std": 0.018,
        "iat_burstiness": 1.45,
        "uplink_pkt_ratio": 0.50,
        "byte_up_down_ratio": 0.88,
        "duration": 6.0,
        "total_packets": 320.0,
        "total_bytes": 120000.0,
        "packets_per_second": 55.0,
        "pkt_size_entropy": 4.0,
        "iat_entropy": 3.4,
    },
    "trojan": {
        "pkt_len_mean": 540.0,
        "pkt_len_std": 200.0,
        "pkt_len_min": 52.0,
        "pkt_len_max": 1440.0,
        "pkt_len_p25": 340.0,
        "pkt_len_p75": 840.0,
        "iat_mean": 0.036,
        "iat_std": 0.024,
        "iat_burstiness": 1.20,
        "uplink_pkt_ratio": 0.45,
        "byte_up_down_ratio": 0.58,
        "duration": 8.2,
        "total_packets": 280.0,
        "total_bytes": 150000.0,
        "packets_per_second": 40.0,
        "pkt_size_entropy": 3.65,
        "iat_entropy": 3.15,
    },
    "vmess": {
        "pkt_len_mean": 480.0,
        "pkt_len_std": 230.0,
        "pkt_len_min": 48.0,
        "pkt_len_max": 1480.0,
        "pkt_len_p25": 280.0,
        "pkt_len_p75": 760.0,
        "iat_mean": 0.026,
        "iat_std": 0.028,
        "iat_burstiness": 1.70,
        "uplink_pkt_ratio": 0.53,
        "byte_up_down_ratio": 1.05,
        "duration": 5.2,
        "total_packets": 360.0,
        "total_bytes": 165000.0,
        "packets_per_second": 70.0,
        "pkt_size_entropy": 3.9,
        "iat_entropy": 3.5,
    },
}

# Larger base scales × default noise produce class overlap for realistic metrics.
_CLASS_SCALES: dict[str, dict[str, float]] = {
    label: {
        "pkt_len_mean": 160.0,
        "pkt_len_std": 80.0,
        "pkt_len_min": 30.0,
        "pkt_len_max": 180.0,
        "pkt_len_p25": 120.0,
        "pkt_len_p75": 140.0,
        "iat_mean": 0.02,
        "iat_std": 0.015,
        "iat_burstiness": 0.55,
        "uplink_pkt_ratio": 0.14,
        "byte_up_down_ratio": 0.45,
        "duration": 3.5,
        "total_packets": 90.0,
        "total_bytes": 45000.0,
        "packets_per_second": 22.0,
        "pkt_size_entropy": 0.75,
        "iat_entropy": 0.65,
    }
    for label in LABELS
}

# Clip ranges: (low, high); None means no bound on that side.
_CLIP_RANGES: dict[str, tuple[float | None, float | None]] = {
    "pkt_len_mean": (1.0, 2000.0),
    "pkt_len_std": (0.0, 1000.0),
    "pkt_len_min": (1.0, 1500.0),
    "pkt_len_max": (1.0, 2000.0),
    "pkt_len_p25": (1.0, 2000.0),
    "pkt_len_p75": (1.0, 2000.0),
    "iat_mean": (1e-6, 10.0),
    "iat_std": (0.0, 10.0),
    "iat_burstiness": (0.0, 20.0),
    "uplink_pkt_ratio": (0.0, 1.0),
    "byte_up_down_ratio": (0.0, 10.0),
    "duration": (1e-3, None),
    "total_packets": (1.0, None),
    "total_bytes": (1.0, None),
    "packets_per_second": (0.0, None),
    "pkt_size_entropy": (0.0, 10.0),
    "iat_entropy": (0.0, 10.0),
}


def _sample_class(
    rng: np.random.Generator,
    label: str,
    n: int,
    noise: float,
) -> dict[str, np.ndarray]:
    means = _CLASS_MEANS[label]
    scales = _CLASS_SCALES[label]
    cols: dict[str, np.ndarray] = {}
    for col in FEATURE_COLUMNS:
        raw = means[col] + noise * scales[col] * rng.standard_normal(n)
        lo, hi = _CLIP_RANGES[col]
        if lo is not None:
            raw = np.maximum(raw, lo)
        if hi is not None:
            raw = np.minimum(raw, hi)
        cols[col] = raw
    return cols


def generate_synthetic_dataset(
    n_per_class: int = 1000,
    seed: int = RANDOM_SEED,
    noise: float = 0.85,
) -> pd.DataFrame:
    """Generate a balanced synthetic flow-feature dataset.

    Each label gets exactly ``n_per_class`` rows. Feature columns follow
    ``FEATURE_COLUMNS``; last column is ``label``. Same ``seed`` yields
    identical frames.
    """
    if n_per_class < 1:
        raise ValueError("n_per_class must be >= 1")
    if noise < 0:
        raise ValueError("noise must be >= 0")

    rng = np.random.default_rng(seed)
    frames: list[pd.DataFrame] = []

    for label in LABELS:
        cols = _sample_class(rng, label, n_per_class, noise)
        frame = pd.DataFrame(cols)
        frame["label"] = label
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    return df[FEATURE_COLUMNS + ["label"]]

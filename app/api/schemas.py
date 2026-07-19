"""Strict request schemas shared by the public API routes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import RANDOM_SEED

ModelName = Literal[
    "decision_tree",
    "svm",
    "random_forest",
    "adaboost",
    "xgboost",
    "lightgbm",
    "voting",
    "stacking",
]

MAX_PREDICT_BATCH = 500


class StrictRequest(BaseModel):
    """Base request model that rejects misspelled/unknown fields."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @model_validator(mode="before")
    @classmethod
    def reject_boolean_scalars(cls, value: object) -> object:
        """Prevent Python's bool-is-int coercion in numeric request fields."""
        if isinstance(value, dict):
            boolean_fields = [key for key, item in value.items() if isinstance(item, bool)]
            if boolean_fields:
                raise ValueError(
                    f"request values must use explicit numbers, not booleans: {boolean_fields}"
                )
        return value


class GenerateRequest(StrictRequest):
    """Synthetic dataset generation parameters."""

    n_per_class: int = Field(default=800, ge=1, le=50_000)
    seed: int = Field(default=RANDOM_SEED, ge=0, le=4_294_967_295)
    noise: float = Field(default=0.85, ge=0.0, le=5.0)


class TrainRequest(StrictRequest):
    """Known models to train, normalized to a unique ordered list."""

    models: list[ModelName] = Field(
        default_factory=lambda: ["random_forest", "xgboost", "voting"],
        min_length=1,
    )

    @field_validator("models")
    @classmethod
    def deduplicate_models(cls, value: list[ModelName]) -> list[ModelName]:
        """Deduplicate while preserving the user's selected order."""
        unique = list(dict.fromkeys(value))
        if len(unique) > 8:
            raise ValueError("at most 8 unique models may be selected")
        return unique


class FeatureSample(StrictRequest):
    """One complete 17-dimensional inference sample."""

    pkt_len_mean: float
    pkt_len_std: float
    pkt_len_min: float
    pkt_len_max: float
    pkt_len_p25: float
    pkt_len_p75: float
    iat_mean: float
    iat_std: float
    iat_burstiness: float
    uplink_pkt_ratio: float
    byte_up_down_ratio: float
    duration: float
    total_packets: float
    total_bytes: float
    packets_per_second: float
    pkt_size_entropy: float
    iat_entropy: float

class PredictRequest(StrictRequest):
    """Bounded batch inference request."""

    samples: list[FeatureSample] = Field(min_length=1, max_length=MAX_PREDICT_BATCH)
    model: ModelName | None = None


class SettingsUpdateRequest(StrictRequest):
    """Partial update for the persisted experiment settings."""

    random_seed: int | None = Field(default=None, ge=0, le=4_294_967_295)
    train_ratio: float | None = Field(default=None, gt=0.0, lt=1.0)
    val_ratio: float | None = Field(default=None, gt=0.0, lt=1.0)
    test_ratio: float | None = Field(default=None, gt=0.0, lt=1.0)
    n_per_class_default: int | None = Field(default=None, ge=1, le=50_000)
    noise_default: float | None = Field(default=None, ge=0.0, le=5.0)

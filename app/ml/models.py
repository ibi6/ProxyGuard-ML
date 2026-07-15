"""Model zoo builders for encrypted proxy traffic classification."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
from sklearn.ensemble import (
    AdaBoostClassifier,
    RandomForestClassifier,
    StackingClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

MODEL_ZOO: dict[str, str] = {
    "decision_tree": "Decision Tree",
    "svm": "SVM (RBF)",
    "random_forest": "Random Forest",
    "adaboost": "AdaBoost",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "voting": "Soft Voting Ensemble",
    "stacking": "Stacking Ensemble",
}

# Boosters that train on integer class ids; reload must still emit string LABELS.
INTEGER_LABEL_MODELS = frozenset({"xgboost", "lightgbm"})


class LabeledClassifier:
    """Estimator + LabelEncoder so joblib reload predicts string labels.

    XGBoost/LightGBM often fit on integer codes; without this wrapper a raw
    booster reload returns ints (0,1,2,...) instead of LABELS strings.
    """

    def __init__(
        self,
        estimator: Any,
        labels: Sequence[str] | None = None,
        label_encoder: LabelEncoder | None = None,
    ) -> None:
        self.estimator = estimator
        if label_encoder is not None:
            self.label_encoder = label_encoder
        else:
            self.label_encoder = LabelEncoder()
            if labels is not None:
                self.label_encoder.fit(list(labels))

    def fit(self, X: Any, y: Any) -> LabeledClassifier:
        y_arr = np.asarray(y)
        if not hasattr(self.label_encoder, "classes_") or len(
            getattr(self.label_encoder, "classes_", [])
        ) == 0:
            self.label_encoder.fit(y_arr)
        y_enc = self.label_encoder.transform(y_arr)
        self.estimator.fit(X, y_enc)
        return self

    def predict(self, X: Any) -> np.ndarray:
        pred = np.asarray(self.estimator.predict(X))
        # Booster may return float codes; inverse_transform needs int indices.
        return self.label_encoder.inverse_transform(pred.astype(int))

    def predict_proba(self, X: Any) -> np.ndarray:
        return self.estimator.predict_proba(X)

    @property
    def classes_(self) -> np.ndarray:
        return np.asarray(self.label_encoder.classes_)

    @property
    def feature_importances_(self) -> Any:
        return getattr(self.estimator, "feature_importances_", None)

    @property
    def named_steps(self) -> Any:
        # Allow pipeline-style unwrapping in feature-importance helpers.
        return getattr(self.estimator, "named_steps", None)

    def get_params(self, deep: bool = True) -> dict[str, Any]:
        return {
            "estimator": self.estimator,
            "label_encoder": self.label_encoder,
        }

    def set_params(self, **params: Any) -> LabeledClassifier:
        if "estimator" in params:
            self.estimator = params["estimator"]
        if "label_encoder" in params:
            self.label_encoder = params["label_encoder"]
        if "labels" in params and params["labels"] is not None:
            self.label_encoder = LabelEncoder()
            self.label_encoder.fit(list(params["labels"]))
        return self


def get_model_zoo() -> dict[str, str]:
    """Return model_name -> display_name mapping."""
    return dict(MODEL_ZOO)


def _require_xgboost():
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "xgboost is required for the 'xgboost' model but failed to import. "
            "Install with: pip install xgboost"
        ) from exc
    return XGBClassifier


def _require_lightgbm():
    try:
        from lightgbm import LGBMClassifier
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "lightgbm is required for the 'lightgbm' model but failed to import. "
            "Install with: pip install lightgbm"
        ) from exc
    return LGBMClassifier


def _base_estimators(seed: int) -> list[tuple[str, Any]]:
    """Diverse base learners used by voting/stacking (all support predict_proba)."""
    XGBClassifier = _require_xgboost()
    LGBMClassifier = _require_lightgbm()
    return [
        (
            "dt",
            DecisionTreeClassifier(max_depth=8, random_state=seed),
        ),
        (
            "rf",
            RandomForestClassifier(
                n_estimators=80,
                max_depth=12,
                n_jobs=-1,
                random_state=seed,
            ),
        ),
        (
            "svm",
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "clf",
                        SVC(
                            kernel="rbf",
                            C=1.0,
                            probability=True,
                            random_state=seed,
                        ),
                    ),
                ]
            ),
        ),
        (
            "xgb",
            XGBClassifier(
                n_estimators=80,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="multi:softprob",
                eval_metric="mlogloss",
                n_jobs=-1,
                random_state=seed,
                verbosity=0,
            ),
        ),
        (
            "lgbm",
            LGBMClassifier(
                n_estimators=80,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.9,
                colsample_bytree=0.9,
                n_jobs=-1,
                random_state=seed,
                verbosity=-1,
            ),
        ),
    ]


def build_model(name: str, seed: int = 42) -> Any:
    """Build a sklearn-compatible estimator (often a Pipeline).

    Raises:
        ValueError: unknown model name
        ImportError: xgboost/lightgbm requested but not importable
    """
    key = (name or "").strip().lower()
    if key not in MODEL_ZOO:
        raise ValueError(f"unknown model: {name!r}; expected one of {sorted(MODEL_ZOO)}")

    if key == "decision_tree":
        return DecisionTreeClassifier(max_depth=10, random_state=seed)

    if key == "svm":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    SVC(
                        kernel="rbf",
                        C=1.0,
                        probability=True,
                        random_state=seed,
                    ),
                ),
            ]
        )

    if key == "random_forest":
        return RandomForestClassifier(
            n_estimators=100,
            max_depth=14,
            n_jobs=-1,
            random_state=seed,
        )

    if key == "adaboost":
        return AdaBoostClassifier(
            estimator=DecisionTreeClassifier(max_depth=3, random_state=seed),
            n_estimators=80,
            learning_rate=0.8,
            random_state=seed,
        )

    if key == "xgboost":
        XGBClassifier = _require_xgboost()
        return XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            eval_metric="mlogloss",
            n_jobs=-1,
            random_state=seed,
            verbosity=0,
        )

    if key == "lightgbm":
        LGBMClassifier = _require_lightgbm()
        return LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            n_jobs=-1,
            random_state=seed,
            verbosity=-1,
        )

    if key == "voting":
        estimators = _base_estimators(seed)
        # Soft voting needs predict_proba on every estimator.
        return VotingClassifier(estimators=estimators, voting="soft", n_jobs=-1)

    if key == "stacking":
        estimators = _base_estimators(seed)
        final = LogisticRegression(max_iter=1000, multi_class="auto", random_state=seed)
        return StackingClassifier(
            estimators=estimators,
            final_estimator=final,
            stack_method="predict_proba",
            n_jobs=-1,
            passthrough=False,
        )

    raise ValueError(f"unknown model: {name!r}")

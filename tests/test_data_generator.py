from collections import Counter

from app.config import LABELS
from app.ml.data_generator import generate_synthetic_dataset
from app.ml.features import validate_feature_frame


def test_generate_shape_and_labels():
    df = generate_synthetic_dataset(n_per_class=50, seed=42, noise=0.15)
    assert len(df) == 200
    assert set(df["label"]) == set(LABELS)
    assert Counter(df["label"]) == {k: 50 for k in LABELS}
    validate_feature_frame(df)


def test_generate_reproducible():
    a = generate_synthetic_dataset(n_per_class=30, seed=7)
    b = generate_synthetic_dataset(n_per_class=30, seed=7)
    assert a.equals(b)

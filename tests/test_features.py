import pandas as pd
import pytest
from app.config import FEATURE_COLUMNS
from app.ml.features import validate_feature_frame


def test_validate_feature_frame_ok():
    row = {c: 1.0 for c in FEATURE_COLUMNS}
    row["label"] = "vmess"
    df = pd.DataFrame([row])
    out = validate_feature_frame(df)
    assert list(out.columns) == FEATURE_COLUMNS + ["label"]
    assert out.iloc[0]["label"] == "vmess"


def test_validate_feature_frame_missing_column():
    df = pd.DataFrame([{"label": "trojan", "pkt_len_mean": 1.0}])
    with pytest.raises(ValueError):
        validate_feature_frame(df)

import pytest
from app.ml.labels import normalize_label


def test_normalize_label_accepts_aliases():
    assert normalize_label("Normal HTTPS") == "normal_https"
    assert normalize_label("shadowsocks") == "shadowsocks"
    assert normalize_label("TROJAN") == "trojan"


def test_normalize_label_rejects_unknown():
    with pytest.raises(ValueError):
        normalize_label("wireguard")

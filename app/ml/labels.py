from app.config import LABEL_DISPLAY, LABELS

_ALIAS = {
    **{k: k for k in LABELS},
    **{v.lower(): k for k, v in LABEL_DISPLAY.items()},
    **{v: k for k, v in LABEL_DISPLAY.items()},
    "https": "normal_https",
    "normal": "normal_https",
    "ss": "shadowsocks",
}


def normalize_label(raw: str) -> str:
    key = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    # also try original display lower
    candidates = [key, str(raw).strip().lower()]
    for c in candidates:
        if c in _ALIAS:
            return _ALIAS[c]
        # map display lower with spaces
        c2 = str(raw).strip().lower()
        for lab, disp in LABEL_DISPLAY.items():
            if c2 == disp.lower():
                return lab
    if key in LABELS:
        return key
    raise ValueError(f"unknown label: {raw}")

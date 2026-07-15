import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DB_PATH = BASE_DIR / "app" / "proxyguard.db"

# Data API uses real DatasetService by default; train/predict may still mock.
USE_MOCK = os.getenv("USE_MOCK", "false").strip().lower() in {"1", "true", "yes", "on"}

RANDOM_SEED = 42
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

LABELS = ("normal_https", "shadowsocks", "trojan", "vmess")
LABEL_DISPLAY = {
    "normal_https": "Normal HTTPS",
    "shadowsocks": "Shadowsocks",
    "trojan": "Trojan",
    "vmess": "VMess",
}

FEATURE_COLUMNS = [
    "pkt_len_mean", "pkt_len_std", "pkt_len_min", "pkt_len_max", "pkt_len_p25", "pkt_len_p75",
    "iat_mean", "iat_std", "iat_burstiness",
    "uplink_pkt_ratio", "byte_up_down_ratio",
    "duration", "total_packets", "total_bytes", "packets_per_second",
    "pkt_size_entropy", "iat_entropy",
]

for d in (DATA_DIR, MODELS_DIR, REPORTS_DIR, FIGURES_DIR):
    d.mkdir(parents=True, exist_ok=True)

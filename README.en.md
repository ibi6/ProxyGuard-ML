# ProxyGuard ML

Undergraduate project: encrypted proxy traffic classification with ensemble learning.

No TLS decryption. Uses 17 flow-level stats. Labels:

- `normal_https`
- `shadowsocks`
- `trojan`
- `vmess`

Stack: FastAPI, scikit-learn / XGBoost / LightGBM, SQLite, simple web UI.

[中文](README.md)

## Data note

Default data is **synthetic** (per-class means + noise). No PCAP sniffer in this repo. Say that clearly in reports.

Typical run: 800 samples/class, seed 42, noise 0.85. Soft Voting macro-F1 ≈ 0.75.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000

Offline:

```bash
python scripts/run_experiments.py --n-per-class 800 --seed 42 --noise 0.85
pytest -q
```

## Env

| Variable | Meaning |
|----------|---------|
| `USE_MOCK=true` | Fake metrics path — don't use for real demos |
| `PROXYGUARD_TOKEN` | If set, write APIs need `X-API-Token` |

## License

MIT. Don't use for unauthorized monitoring.

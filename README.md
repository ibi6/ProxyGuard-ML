<div align="center">

<img src="assets/logo.svg" width="72" alt="ProxyGuard ML" />

# ProxyGuard ML

### Encrypted proxy traffic recognition — without decrypting a single byte

Side-channel ensemble learning · FastAPI ops console · reproducible research demos

[English](README.en.md) · [简体中文](README.md) · [Architecture](docs/ARCHITECTURE.md)

<br/>

![Stars](https://img.shields.io/github/stars/ibi6/ProxyGuard-ML?style=for-the-badge&label=STARS&logo=github&color=0969da)
![Forks](https://img.shields.io/github/forks/ibi6/ProxyGuard-ML?style=for-the-badge&label=FORKS&logo=github&color=1f883d)
![Last Commit](https://img.shields.io/github/last-commit/ibi6/ProxyGuard-ML?style=for-the-badge&label=LAST%20COMMIT&color=238636)
![CI](https://img.shields.io/github/actions/workflow/status/ibi6/ProxyGuard-ML/ci.yml?branch=main&style=for-the-badge&label=CI)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-2ea44f?style=for-the-badge)
![Version](https://img.shields.io/badge/version-0.3.0-111827?style=for-the-badge)

</div>

<p align="center">
  <img src="assets/banner.svg" alt="banner" width="100%" />
</p>

---

## Why this project

TLS and modern proxies hide payloads. **ProxyGuard ML never decrypts traffic.**  
It classifies flows from **17 statistical features** into:

`normal_https` · `shadowsocks` · `trojan` · `vmess`

| Layer | Choice |
|-------|--------|
| API / UI | FastAPI + Jinja2 console |
| ML | scikit-learn · XGBoost · LightGBM |
| Storage | CSV / joblib / SQLite task log |
| Ops | Docker Compose · GitHub Actions · optional API token |

> **Data honesty:** default samples are **synthetic** (seeded Gaussians).  
> No PCAP sniffer ships here. Publish numbers only with that caveat.

---

## Highlights

- **8-model zoo** — DT, SVM, RF, AdaBoost, XGBoost, LightGBM, Soft Voting, Stacking  
- **End-to-end console** — generate/upload → train (cancellable) → predict → export  
- **Reproducible experiments** — seed / noise / split settings persist to SQLite  
- **Engineering guardrails** — upload limits, Inf checks, train mutex, security headers  
- **CI** — ruff + pytest matrix (3.11/3.12) + Docker build on `main`  

<p align="center">
  <img src="assets/architecture.svg" width="100%" alt="architecture" />
</p>

```text
Browser  →  FastAPI (/api/* + pages)
         →  Services (dataset · train · predict · experiments · settings)
         →  ML core (generator · models · train · evaluate · predict)
         →  data/ · models/ · reports/ · SQLite
```

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/schema.sql](docs/schema.sql)

---

## Quick start

### Requirements

- Python **3.10+**
- ~2 GB disk for deps + models

### Install & run

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML

python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Unix:    source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt

# optional local config
cp .env.example .env

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

| URL | |
|-----|--|
| http://127.0.0.1:8000 | Web console |
| http://127.0.0.1:8000/docs | OpenAPI |
| http://127.0.0.1:8000/api/health | Health |

### Makefile

```bash
make install      # runtime deps
make dev          # + ruff
make test         # pytest
make lint         # ruff + compileall
make run          # uvicorn
make experiment   # offline n=800
make docker-up    # compose
```

### Offline experiment

```bash
python scripts/run_experiments.py --n-per-class 800 --seed 42 --noise 0.85
pytest -q
```

---

## Screenshots / UI

<p align="center">
  <img src="assets/console-mock.svg" width="100%" alt="console" />
</p>

| Path | Page |
|------|------|
| `/` | Dashboard |
| `/data` | Synthetic generate / CSV upload |
| `/train` | Multi-model training + cancel |
| `/predict` | Online inference |
| `/experiments` | Metrics & export |
| `/settings` | Seed & split ratios |

---

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness |
| GET | `/api/system` | Runtime snapshot |
| POST | `/api/data/generate` | Synthetic dataset |
| POST | `/api/data/upload` | CSV (≤20MB) |
| POST | `/api/train` | Start job |
| POST | `/api/train/{id}/cancel` | Cancel between models |
| GET | `/api/train` · `/train/{id}` | List / detail |
| GET | `/api/models` | Zoo + metrics |
| POST | `/api/predict` | Inference |
| GET | `/api/predict/stats` | Log count |
| GET | `/api/experiments` | Comparison |
| GET | `/api/report/export` | Zip/meta |
| GET/PUT | `/api/settings` | Persisted config |

**Auth (optional):** set `PROXYGUARD_TOKEN` → send `X-API-Token` on write routes.  
Browser: `localStorage.setItem('pg_api_token', '...')`.

See interactive docs at `/docs` when the server is running.

---

## Benchmark (synthetic)

<p align="center">
  <img src="assets/leaderboard.svg" width="100%" alt="leaderboard" />
</p>

Protocol: `n_per_class=800`, `seed=42`, `noise=0.85`, split `0.70/0.15/0.15`.

| Rank | Model | Accuracy | Macro-F1 |
|:----:|-------|---------:|---------:|
| 1 | **Soft Voting** | **0.752** | **0.752** |
| 2 | SVM (RBF) | 0.750 | 0.748 |
| 3 | Stacking | 0.746 | 0.744 |
| 4 | Random Forest | 0.740 | 0.735 |
| 5 | XGBoost | 0.727 | 0.725 |
| 6 | LightGBM | 0.725 | 0.723 |
| 7 | AdaBoost | 0.690 | 0.694 |
| 8 | Decision Tree | 0.600 | 0.604 |

DT `max_depth` and RF `n_estimators` are lightly tuned on the **validation** split; **public metrics are test-set only**.

---

## Docker

```bash
docker compose up --build
# → http://127.0.0.1:8000
```

---

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `USE_MOCK` | `false` | Simulated metrics path — **keep false** for real runs |
| `PROXYGUARD_TOKEN` | empty | If set, protect write APIs |
| `PROXYGUARD_MAX_UPLOAD_BYTES` | 20MB | CSV size cap |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

Copy [`.env.example`](.env.example) → `.env` for local overrides.

---

## Repository layout

```text
ProxyGuard-ML/
├── app/                 # FastAPI app, services, ML, UI
├── tests/               # pytest
├── scripts/             # offline experiment runners
├── docs/                # architecture, schema, guides
├── assets/              # README diagrams
├── data/ models/ reports/
├── Dockerfile · docker-compose.yml
├── requirements.txt · requirements-dev.txt
├── pyproject.toml · Makefile
└── .github/workflows/ci.yml
```

---

## Roadmap

- [ ] PCAP → flow aggregation → `FEATURE_COLUMNS` pipeline  
- [ ] Self-hosted static assets (drop CDN)  
- [ ] Optional multi-user auth profile  
- [ ] Nested CV & structured HPO reports  
- [ ] Release workflow on git tags  

---

## Contributing & security

- [CONTRIBUTING.md](CONTRIBUTING.md)  
- [SECURITY.md](SECURITY.md)  
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)  
- [CHANGELOG.md](CHANGELOG.md)  
- [docs/OPENSOURCE_SCORECARD.md](docs/OPENSOURCE_SCORECARD.md)  

---

## License

[MIT](LICENSE) © ProxyGuard ML Contributors  

Do **not** use for unauthorized network monitoring. Always disclose synthetic vs real data when publishing results.

<p align="center">
  <img src="assets/social.svg" width="100%" alt="social" />
  <br/>
  <a href="https://github.com/ibi6/ProxyGuard-ML"><b>github.com/ibi6/ProxyGuard-ML</b></a>
</p>

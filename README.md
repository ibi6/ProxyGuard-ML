<div align="center">

<img src="assets/logo.svg" width="72" alt="ProxyGuard ML" />

# ProxyGuard ML · 加密代理流量识别

**基于集成学习的加密代理流量识别系统**

FastAPI · scikit-learn · XGBoost · LightGBM · Jinja2 · SQLite

[English](README.en.md) · [简体中文](README.md)

<br/>

![Stars](https://img.shields.io/github/stars/ibi6/ProxyGuard-ML?style=for-the-badge&label=STARS&logo=github&color=0969da)
![Forks](https://img.shields.io/github/forks/ibi6/ProxyGuard-ML?style=for-the-badge&label=FORKS&logo=github&color=1f883d)
![Last Commit](https://img.shields.io/github/last-commit/ibi6/ProxyGuard-ML?style=for-the-badge&label=LAST%20COMMIT&color=238636)
![CI](https://img.shields.io/github/actions/workflow/status/ibi6/ProxyGuard-ML/ci.yml?branch=main&style=for-the-badge&label=CI)

<br/>

![Python](https://img.shields.io/badge/PYTHON-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FASTAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![scikit-learn](https://img.shields.io/badge/SCIKIT--LEARN-1.5-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBOOST-2.1-E85D04?style=for-the-badge)
![LightGBM](https://img.shields.io/badge/LIGHTGBM-4.5-9B59B6?style=for-the-badge)
![License](https://img.shields.io/badge/LICENSE-MIT-2ea44f?style=for-the-badge)

<br/>

[Features](#features) ·
[Architecture](#architecture) ·
[Quick Start](#quick-start) ·
[API](#api) ·
[Benchmark](#benchmark) ·
[Docker](#docker)

</div>

<p align="center">
  <img src="assets/banner.svg" alt="banner" width="100%" />
</p>

---

## Features

| | |
|:--|:--|
| **No payload decrypt** | 17-D flow statistics only (length / IAT / direction / scale / entropy) |
| **8-model zoo** | DT · SVM · RF · AdaBoost · XGBoost · LightGBM · Soft Voting · Stacking |
| **Web console** | Data → Train → Predict → Experiments → Settings |
| **Reproducible** | Seeded synthetic generator + CSV upload (aligned schema) |
| **Ops-ready bits** | Background train jobs, SQLite task log, zip export, optional API token |
| **CI / Docker** | GitHub Actions + Compose |

**Task:** 4-class supervised learning — `normal_https` / `shadowsocks` / `trojan` / `vmess`

> Default data is **synthetic** (class-conditional Gaussians with controlled overlap).  
> This repo does **not** ship PCAP capture. Metrics reflect lab separability, not open-internet DPI accuracy.

---

## Architecture

<p align="center">
  <img src="assets/architecture.svg" width="100%" alt="architecture" />
</p>

```text
Browser (Jinja2 + Chart.js)
        │
        ▼
FastAPI  /api/data | train | predict | experiments | settings
        │
        ▼
Services → ML core (generator · train · evaluate · predict)
        │
        ▼
data/ · models/*.joblib · reports/ · SQLite
```

<p align="center">
  <img src="assets/pipeline.svg" width="100%" alt="pipeline" />
</p>

---

## Quick Start

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -U pip && pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

| URL | |
|-----|--|
| http://127.0.0.1:8000 | Console |
| http://127.0.0.1:8000/docs | OpenAPI |
| http://127.0.0.1:8000/api/health | Health |

**Demo loop:** generate ~800 samples/class → train (include `voting`) → predict → export experiments.

```bash
python scripts/run_experiments.py --n-per-class 800 --seed 42 --noise 0.85
pytest -q
```

---

## API

| Method | Path | |
|--------|------|--|
| GET | `/api/health` | Liveness |
| GET | `/api/system` | Runtime snapshot |
| POST | `/api/data/generate` | Synthetic data |
| POST | `/api/data/upload` | CSV (≤20MB, schema-checked) |
| POST | `/api/train` | Start job (single-flight) |
| GET | `/api/train/{id}` | Task status + progress |
| POST | `/api/predict` | Inference |
| GET | `/api/predict/stats` | Predict log count |
| GET | `/api/experiments` | Metrics |
| GET | `/api/report/export` | Zip bundle |
| GET/PUT | `/api/settings` | Seed & split ratios |

Optional: set `PROXYGUARD_TOKEN` → write APIs require header `X-API-Token`.  
Browser: `localStorage.setItem('pg_api_token', '...')`.

---

## Benchmark

<p align="center">
  <img src="assets/leaderboard.svg" width="100%" alt="leaderboard" />
</p>

Synthetic protocol (`n_per_class=800`, `seed=42`, `noise=0.85`):

| Rank | Model | Acc | Macro-F1 |
|:----:|-------|----:|---------:|
| 1 | **Soft Voting** | **0.752** | **0.752** |
| 2 | SVM | 0.750 | 0.748 |
| 3 | Stacking | 0.746 | 0.744 |
| 4 | Random Forest | 0.740 | 0.735 |
| 5 | XGBoost | 0.727 | 0.725 |
| 6 | LightGBM | 0.725 | 0.723 |
| 7 | AdaBoost | 0.690 | 0.694 |
| 8 | Decision Tree | 0.600 | 0.604 |

Decision tree `max_depth` is lightly tuned on the validation split; **reported metrics are always test-set**.

---

## Docker

```bash
docker compose up --build
```

---

## Layout

```text
app/           # API · services · ML · UI
tests/         # pytest
scripts/       # offline experiments
docs/          # design notes · schema.sql
assets/        # diagrams for this README
data/ models/ reports/   # runtime artifacts (local)
```

---

## Limits

- Synthetic-by-default (not real proxy captures)
- No multi-user auth by default (optional token only)
- In-process training thread; one job at a time
- No PCAP pipeline — upload 17-D CSV for external features

---

## License

[MIT](LICENSE). Do not use for unauthorized monitoring. Always state data source when publishing numbers.

<p align="center">
  <img src="assets/social.svg" width="100%" alt="card" />
  <br/>
  <a href="https://github.com/ibi6/ProxyGuard-ML"><b>github.com/ibi6/ProxyGuard-ML</b></a>
</p>

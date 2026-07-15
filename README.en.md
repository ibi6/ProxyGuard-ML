<div align="center">

<img src="assets/logo.svg" width="72" alt="ProxyGuard ML logo" />

# ProxyGuard ML · Encrypted Proxy Traffic Recognition

**Design and Implementation of an Ensemble-Learning System for Encrypted Proxy Traffic Identification**

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

[Features](#-features) ·
[Screenshots](#-screenshots) ·
[Architecture](#-architecture) ·
[Quick Start](#-quick-start) ·
[API](#-api) ·
[Benchmark](#-benchmark) ·
[Demo](#-demo)

</div>

<br/>

<div align="center">
  <img src="assets/banner.svg" alt="ProxyGuard ML banner" width="100%" />
</div>

---

## ✨ Features

| | Capability | Detail |
|:---:|:---|:---|
| 🔒 | **Zero payload decrypt** | Side-channel flow stats only — no TLS keys, no DPI plaintext |
| 🧠 | **8-model ensemble zoo** | DT · SVM · RF · AdaBoost · XGBoost · LightGBM · Soft Voting · Stacking |
| 📊 | **17-D feature schema** | Packet length · IAT · direction · scale · entropy |
| 🖥️ | **Ops console** | Dashboard · Data · Train · Predict · Experiments · Settings |
| 🔁 | **Reproducible** | Fixed seed (`42`), offline runners, ablation scripts |
| 🐳 | **One-command Docker** | Compose stack with persistent volumes |
| ✅ | **CI ready** | GitHub Actions · pytest · multi-Python matrix |

**Task definition**

| Item | Value |
|------|-------|
| Task | 4-class supervised recognition |
| Labels | `normal_https` · `shadowsocks` · `trojan` · `vmess` |
| Runtime | FastAPI + Jinja2 + SQLite |
| Data | Seeded synthetic generator **or** schema-aligned CSV |

> **Research honesty.** Defaults use **synthetic** features with intentional class overlap.  
> No NIC sniffer / PCAP parser is shipped. Metrics describe lab separability — not open-internet DPI accuracy.

---

## 🖼️ Screenshots

<div align="center">
  <img src="assets/console-mock.svg" alt="Console preview" width="100%" />
  <p><sub>Operations dashboard mock · live UI at <code>http://127.0.0.1:8000</code></sub></p>
</div>

| Route | Workspace |
|-------|-----------|
| `/` | Operations dashboard |
| `/data` | Generate / upload / preview datasets |
| `/train` | Multi-model training jobs |
| `/predict` | Online 17-D inference |
| `/experiments` | Metrics, charts, zip export |
| `/settings` | Seed, split ratios, persistence |

---

## 🏗️ Architecture

<div align="center">
  <img src="assets/architecture.svg" alt="Architecture" width="100%" />
  <br/><br/>
  <img src="assets/pipeline.svg" alt="Pipeline" width="100%" />
</div>

```text
Browser (Jinja2 + Chart.js)
        │
        ▼
FastAPI  ── /api/data | train | predict | experiments | settings
        │
        ▼
Services ── Dataset · Train · Predict · Experiment · Settings
        │
        ▼
ML Core  ── generator · features · models · train · evaluate · predict
        │
        ▼
Storage  ── data/ · models/*.joblib · reports/ · SQLite
```

---

## 🚀 Quick Start

### Requirements

- Python **3.10+** (3.11 / 3.12 recommended)
- ~2 GB free disk
- Windows · macOS · Linux

### Install & run

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML

python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Unix:    source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000 | Web console |
| http://127.0.0.1:8000/api/health | Health check |
| http://127.0.0.1:8000/docs | OpenAPI |

<details>
<summary><b>Make targets</b></summary>

```bash
make install      # deps
make test         # pytest
make run          # uvicorn :8000
make experiment   # offline n=1000 full zoo
make smoke        # tiny smoke train
make docker-up    # compose stack
```

</details>

### Docker

```bash
docker compose up --build
# → http://127.0.0.1:8000
```

---

## 🔌 API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness |
| `POST` | `/api/data/generate` | Synthetic dataset |
| `POST` | `/api/data/upload` | CSV import |
| `GET` | `/api/data/summary` · `/preview` | Dataset introspection |
| `POST` | `/api/train` | Start training job |
| `GET` | `/api/train` · `/train/{id}` | Job list / detail |
| `GET` | `/api/models` | Model zoo |
| `POST` | `/api/predict` | Inference |
| `GET` | `/api/experiments` | Metrics payload |
| `GET` | `/api/report/export` | Zip export |
| `GET`/`PUT` | `/api/settings` | Runtime config |

Interactive docs: `/docs` · ReDoc: `/redoc`

---

## 📈 Benchmark

<div align="center">
  <img src="assets/leaderboard.svg" alt="Leaderboard" width="100%" />
</div>

Controlled synthetic setting (`n_per_class=800`, `seed=42`, `noise=0.85`):

| Rank | Model | Accuracy | Macro F1 |
|:----:|-------|---------:|---------:|
| 🥇 | **Soft Voting** | **0.752** | **0.752** |
| 🥈 | SVM (RBF) | 0.750 | 0.748 |
| 🥉 | Stacking | 0.746 | 0.744 |
| 4 | Random Forest | 0.740 | 0.735 |
| 5 | XGBoost | 0.727 | 0.725 |
| 6 | LightGBM | 0.725 | 0.723 |
| 7 | AdaBoost | 0.690 | 0.694 |
| 8 | Decision Tree | 0.600 | 0.604 |

**Noise ablation** (`n=500/class`): best F1 ≈ **0.86** @ `noise=0.55` → ≈ **0.74** @ `noise=0.85`.

### Model zoo

| Key | Role |
|-----|------|
| `decision_tree` | Interpretable baseline |
| `svm` | RBF SVM (scaled) |
| `random_forest` | Bagging |
| `adaboost` | Boosting |
| `xgboost` / `lightgbm` | Gradient boosting |
| `voting` | Soft probability ensemble |
| `stacking` | Meta-learner ensemble |

### 17-D features

| Group | Columns |
|-------|---------|
| Packet length | `pkt_len_mean` `pkt_len_std` `pkt_len_min` `pkt_len_max` `pkt_len_p25` `pkt_len_p75` |
| Inter-arrival | `iat_mean` `iat_std` `iat_burstiness` |
| Direction | `uplink_pkt_ratio` `byte_up_down_ratio` |
| Flow scale | `duration` `total_packets` `total_bytes` `packets_per_second` |
| Complexity | `pkt_size_entropy` `iat_entropy` |

---

## 🎬 Demo

**Five-minute loop**

1. **Data** → generate ~1000 samples / class  
2. **Train** → enable `random_forest`, `xgboost`, `voting` (or all 8)  
3. **Predict** → run the sample 17-D vector  
4. **Experiments** → compare F1 / export zip  

**Headless**

```bash
python scripts/run_experiments.py --n-per-class 1000 --seed 42
python scripts/run_experiments.py --n-per-class 200 --seed 42 --models decision_tree,random_forest
```

**Tests**

```bash
pytest -q
# or: make test
```

---

## 📁 Repository

```text
ProxyGuard-ML/
├── app/                 # FastAPI · services · ML core · UI
├── tests/               # API + ML tests
├── scripts/             # offline experiment & ablation
├── docs/                # design + experiment guides
├── assets/              # logos, diagrams, social cards
├── data/ models/ reports/
├── Dockerfile · docker-compose.yml
└── pyproject.toml · Makefile · CITATION.cff
```

---

## ⚠️ Limitations

| Constraint | Implication |
|------------|-------------|
| Synthetic-by-default | Not real Shadowsocks / Trojan / VMess captures |
| No PCAP pipeline | Bring your own features or extend the extractor |
| No authn / authz | Bind to `127.0.0.1` for demos |
| Threaded training | Heavy full-zoo runs can slow the UI process |

---

## 🗺️ Roadmap

- [ ] PCAP → flow aggregation → `FEATURE_COLUMNS` pipeline  
- [ ] More protocols (OpenVPN, WireGuard, …)  
- [ ] Nested CV + structured hyperparameter search  
- [ ] Class imbalance & synthetic→real domain shift  
- [ ] Optional streaming / mirror-path detector  
- [ ] Hardened multi-user deployment profile  

---

## 📚 Documentation

| Resource | Link |
|----------|------|
| 🇨🇳 Chinese README (default) | [README.md](README.md) |
| Docs hub | [docs/README.md](docs/README.md) |
| System design | [docs/system-design.md](docs/system-design.md) |
| Experiment guide | [docs/experiment-guide.md](docs/experiment-guide.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| Cite | [CITATION.cff](CITATION.cff) |

---

## 📄 License & ethics

**MIT** — see [LICENSE](LICENSE).

For **education, research, and defensive demos**.  
Do **not** use for unauthorized monitoring. Always state data source (synthetic vs real).

---

<div align="center">

<img src="assets/social.svg" width="100%" alt="social card" />

<br/>

**[⭐ Star this repo](https://github.com/ibi6/ProxyGuard-ML)** if it helps your research or coursework.

<sub>FastAPI · scikit-learn · XGBoost · LightGBM · ensemble learning</sub><br/>
<a href="https://github.com/ibi6/ProxyGuard-ML"><b>github.com/ibi6/ProxyGuard-ML</b></a>

</div>

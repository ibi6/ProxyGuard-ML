<p align="center">
  <img src="assets/logo.svg" width="96" alt="ProxyGuard ML logo" />
</p>

<h1 align="center">ProxyGuard ML</h1>

<p align="center">
  <b>Encrypted proxy traffic recognition — without decrypting a single byte.</b><br/>
  Side-channel ensemble learning · FastAPI ops console · reproducible research demo
</p>

<p align="center">
  <a href="https://github.com/ibi6/ProxyGuard-ML/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/ibi6/ProxyGuard-ML/actions/workflows/ci.yml/badge.svg" /></a>
  <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white" /></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" /></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-22c55e" /></a>
  <a href="https://github.com/ibi6/ProxyGuard-ML/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/ibi6/ProxyGuard-ML?style=social" /></a>
  <img alt="Models" src="https://img.shields.io/badge/models-8_ensemble_zoo-14b8a6" />
  <img alt="Decrypt" src="https://img.shields.io/badge/payload_decrypt-never-0ea5e9" />
  <img alt="Version" src="https://img.shields.io/badge/version-0.2.0-111827" />
</p>

<p align="center">
  <a href="#-why-this-exists">Why</a> ·
  <a href="#-quickstart">Quickstart</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-benchmark-snapshot">Benchmark</a> ·
  <a href="#-api-surface">API</a> ·
  <a href="#-docker">Docker</a> ·
  <a href="docs/README.md">Docs</a>
</p>

<p align="center">
  <img src="assets/banner.svg" alt="ProxyGuard ML banner" width="100%" />
</p>

---

## Why this exists

TLS and modern proxy tunnels make **payload inspection useless** without keys — and often illegal without authorization.  
ProxyGuard ML takes the other path: treat each bidirectional flow as a **statistical fingerprint**.

```text
encrypted bytes  ──►  17 flow-level features  ──►  ensemble classifiers  ──►  class + confidence
                         (no DPI decrypt)
```

| Dimension | Spec |
|-----------|------|
| **Task** | 4-class supervised recognition |
| **Labels** | `normal_https` · `shadowsocks` · `trojan` · `vmess` |
| **Features** | Fixed **17-D** flow statistics (length / IAT / direction / scale / entropy) |
| **Models** | DT · SVM · RF · AdaBoost · XGBoost · LightGBM · **Soft Voting** · **Stacking** |
| **Runtime** | FastAPI monolith + Jinja2 console + SQLite job store |
| **Data** | Seeded synthetic generator **or** schema-aligned CSV upload |

> **Research honesty.** Defaults use **synthetic** class-conditional features with intentional overlap.  
> This repository does **not** ship a NIC sniffer or PCAP parser. Metrics describe separability under a controlled lab setting — not production DPI accuracy on the open internet.

---

## Console preview

<p align="center">
  <img src="assets/console-mock.svg" alt="ProxyGuard console mock" width="100%" />
</p>

| Route | Workspace |
|-------|-----------|
| `/` | Operations dashboard |
| `/data` | Generate / upload / preview datasets |
| `/train` | Multi-model training jobs |
| `/predict` | Online 17-D inference |
| `/experiments` | Metrics, charts, zip export |
| `/settings` | Seed, split ratios, persistence |

---

## Feature matrix

<table>
<tr>
<td width="50%">

### Product
- End-to-end Web console (not a notebook dump)
- Background training with task progress
- Soft Voting & Stacking vs strong singles
- Paper-ready plots (accuracy, F1, CM, importance)
- Offline runners for headless CI / batch labs

</td>
<td width="50%">

### Engineering
- Layered architecture (API → service → ML)
- Fixed feature schema + label normalization
- Reproducible seeds (`42` by default)
- pytest suite + GitHub Actions matrix
- Docker / Compose one-command demo

</td>
</tr>
</table>

---

## Architecture

<p align="center">
  <img src="assets/architecture.svg" alt="Architecture diagram" width="100%" />
</p>

<p align="center">
  <img src="assets/pipeline.svg" alt="Inference pipeline" width="100%" />
</p>

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

## Quickstart

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

Open **http://127.0.0.1:8000** · Health **http://127.0.0.1:8000/api/health** · OpenAPI **http://127.0.0.1:8000/docs**

<details>
<summary><b>Make targets</b></summary>

```bash
make install      # deps
make test         # pytest
make run          # uvicorn on :8000
make experiment   # offline n=1000 full zoo
make smoke        # tiny offline smoke
make docker-up    # compose stack
```

</details>

### Five-minute demo loop

1. **Data** → generate ~1000 samples / class  
2. **Train** → enable `random_forest`, `xgboost`, `voting` (or all 8)  
3. **Predict** → run the sample 17-D vector  
4. **Experiments** → compare F1 / export zip  

### Headless experiment

```bash
python scripts/run_experiments.py --n-per-class 1000 --seed 42
python scripts/run_experiments.py --n-per-class 200 --seed 42 --models decision_tree,random_forest
```

---

## Benchmark snapshot

<p align="center">
  <img src="assets/leaderboard.svg" alt="Model leaderboard" width="100%" />
</p>

Controlled synthetic setting (`n_per_class=800`, `seed=42`, `noise=0.85`):

| Rank | Model | Accuracy | Macro F1 |
|:----:|-------|---------:|---------:|
| 1 | **Soft Voting** | **0.752** | **0.752** |
| 2 | SVM (RBF) | 0.750 | 0.748 |
| 3 | Stacking | 0.746 | 0.744 |
| 4 | Random Forest | 0.740 | 0.735 |
| 5 | XGBoost | 0.727 | 0.725 |
| 6 | LightGBM | 0.725 | 0.723 |
| 7 | AdaBoost | 0.690 | 0.694 |
| 8 | Decision Tree | 0.600 | 0.604 |

**Noise ablation** (`n=500/class`): best F1 ≈ **0.86** @ `noise=0.55` → ≈ **0.74** @ `noise=0.85`.  
Ensembles stay competitive as class overlap increases — full tables in `reports/ablation_results.json`.

---

## Model zoo

| Key | Role | Notes |
|-----|------|-------|
| `decision_tree` | Baseline | Interpretable, higher variance |
| `svm` | Kernel baseline | `StandardScaler` + RBF |
| `random_forest` | Bagging | Strong tabular default |
| `adaboost` | Boosting | Classic adaptive boost |
| `xgboost` | GBDT | Label-aware wrapper for string classes |
| `lightgbm` | GBDT | Fast histogram boosting |
| `voting` | Soft ensemble | Probability average of strong bases |
| `stacking` | Meta ensemble | LogisticRegression on base probs |

Default split **70 / 15 / 15** · metrics use **macro** averaging.

### 17-D feature schema

| Group | Columns |
|-------|---------|
| Packet length | `pkt_len_mean` `pkt_len_std` `pkt_len_min` `pkt_len_max` `pkt_len_p25` `pkt_len_p75` |
| Inter-arrival | `iat_mean` `iat_std` `iat_burstiness` |
| Direction | `uplink_pkt_ratio` `byte_up_down_ratio` |
| Flow scale | `duration` `total_packets` `total_bytes` `packets_per_second` |
| Complexity | `pkt_size_entropy` `iat_entropy` |

---

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness |
| `POST` | `/api/data/generate` | Synthetic dataset |
| `POST` | `/api/data/upload` | CSV import |
| `GET` | `/api/data/summary` · `/preview` | Dataset introspection |
| `POST` | `/api/train` | Start job |
| `GET` | `/api/train` · `/train/{id}` | Job list / detail |
| `GET` | `/api/models` | Zoo registry |
| `POST` | `/api/predict` | Inference |
| `GET` | `/api/experiments` | Metrics payload |
| `GET` | `/api/report/export` | Zip export |
| `GET`/`PUT` | `/api/settings` | Runtime config |

Interactive docs: `/docs` · ReDoc: `/redoc`

---

## Docker

```bash
docker compose up --build
# → http://127.0.0.1:8000
```

```bash
docker build -t proxyguard-ml .
docker run --rm -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/models:/app/models" \
  -v "$(pwd)/reports:/app/reports" \
  proxyguard-ml
```

`data/`, `models/`, and `reports/` are volume-mounted so experiments survive restarts.

---

## Repository map

```text
ProxyGuard-ML/
├── app/                 # FastAPI · services · ML core · templates · static
├── tests/               # API + ML unit tests
├── scripts/             # offline experiment & ablation
├── docs/                # design + experiment guides
├── assets/              # logos, diagrams, social cards
├── data/ models/ reports/
├── Dockerfile · docker-compose.yml
├── pyproject.toml · Makefile · CITATION.cff
└── .github/workflows/ci.yml
```

---

## Testing & quality gates

```bash
pytest -q
# or
make test
```

CI on every push/PR to `main`:

| Job | What |
|-----|------|
| **test** | Python **3.11** + **3.12** matrix, full pytest |
| **lint-light** | `compileall` on `app` / `scripts` / `tests` |

---

## Limitations

| Constraint | Implication |
|------------|-------------|
| Synthetic-by-default data | Not real Shadowsocks / Trojan / VMess captures |
| No PCAP pipeline | Bring your own features or extend the extractor |
| No authn / authz | Bind to `127.0.0.1` for demos |
| Threaded training | Heavy full-zoo runs can slow the UI process |

---

## Roadmap

- [ ] PCAP → flow aggregation → `FEATURE_COLUMNS` pipeline  
- [ ] Additional protocols (OpenVPN, WireGuard, …)  
- [ ] Nested CV + structured hyperparameter search  
- [ ] Class imbalance & synthetic→real domain shift studies  
- [ ] Optional streaming / mirror-path detector  
- [ ] Hardened multi-user deployment profile  

---

## Documentation & community

| Resource | Link |
|----------|------|
| Docs hub | [docs/README.md](docs/README.md) |
| System design | [docs/system-design.md](docs/system-design.md) |
| Experiment guide | [docs/experiment-guide.md](docs/experiment-guide.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Code of conduct | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| Cite this software | [CITATION.cff](CITATION.cff) |

---

## License & ethics

**MIT** — see [LICENSE](LICENSE).

ProxyGuard ML is for **education, research, and defensive analysis demos**.  
Do **not** deploy it for unauthorized monitoring. When you publish numbers, **state the data source** (synthetic vs real) explicitly.

---

<p align="center">
  <img src="assets/social.svg" width="100%" alt="ProxyGuard social card" />
</p>

<p align="center">
  <sub>FastAPI · scikit-learn · XGBoost · LightGBM · ensemble learning</sub><br/>
  <a href="https://github.com/ibi6/ProxyGuard-ML"><b>github.com/ibi6/ProxyGuard-ML</b></a>
</p>

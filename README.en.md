<div align="center">

<img src="assets/logo.svg" width="72" alt="ProxyGuard ML" />

# ProxyGuard ML

**Encrypted proxy traffic recognition with ensemble learning**

FastAPI · scikit-learn · XGBoost · LightGBM · Jinja2 · SQLite

[English](README.en.md) · [简体中文](README.md)

<br/>

![Stars](https://img.shields.io/github/stars/ibi6/ProxyGuard-ML?style=for-the-badge&label=STARS&logo=github&color=0969da)
![Forks](https://img.shields.io/github/forks/ibi6/ProxyGuard-ML?style=for-the-badge&label=FORKS&logo=github&color=1f883d)
![CI](https://img.shields.io/github/actions/workflow/status/ibi6/ProxyGuard-ML/ci.yml?branch=main&style=for-the-badge&label=CI)
![Python](https://img.shields.io/badge/PYTHON-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/LICENSE-MIT-2ea44f?style=for-the-badge)

</div>

<p align="center">
  <img src="assets/banner.svg" width="100%" alt="banner" />
</p>

Side-channel **17-D flow features** → multi-model training → web console.  
**No TLS payload decryption.** Default data is **synthetic** (reproducible); CSV upload supported.

## Quick start

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML
python -m venv .venv && source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

→ http://127.0.0.1:8000 · OpenAPI `/docs` · Health `/api/health`

```bash
python scripts/run_experiments.py --n-per-class 800 --seed 42 --noise 0.85
pytest -q
docker compose up --build   # optional
```

## Highlights

- Model zoo: DT, SVM, RF, AdaBoost, XGBoost, LightGBM, Soft Voting, Stacking  
- Background training with progress + SQLite task history  
- Settings (seed / split) applied on next train  
- Optional `PROXYGUARD_TOKEN` + `X-API-Token` for write APIs  
- Benchmark snapshot: Soft Voting macro-F1 ≈ **0.75** @ 800/class, seed 42, noise 0.85  

Full Chinese docs & architecture diagrams: see [README.md](README.md).

## License

MIT. Not for unauthorized monitoring.

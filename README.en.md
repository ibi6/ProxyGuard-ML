<div align="center">

<img src="assets/logo.svg" width="72" alt="ProxyGuard ML" />

# ProxyGuard ML

**Encrypted proxy traffic recognition with ensemble learning**

![CI](https://img.shields.io/github/actions/workflow/status/ibi6/ProxyGuard-ML/ci.yml?branch=main&style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-2ea44f?style=for-the-badge)
![Version](https://img.shields.io/badge/version-0.3.0-111827?style=for-the-badge)

[简体中文](README.md) · [Architecture](docs/ARCHITECTURE.md)

</div>

<p align="center"><img src="assets/banner.svg" width="100%" alt="banner" /></p>

Classifies flows into `normal_https` / `shadowsocks` / `trojan` / `vmess` using **17-D side-channel features**. **No TLS decryption.** Default data is **synthetic**.

## Install

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

→ http://127.0.0.1:8000 · OpenAPI `/docs` · `make test` · `make docker-up`

## Stack

FastAPI · scikit-learn · XGBoost · LightGBM · SQLite · Docker · GitHub Actions (ruff + pytest)

## Benchmark (synthetic, n=800/class, seed=42, noise=0.85)

Soft Voting macro-F1 ≈ **0.75** (best). Full table and diagrams: [README.md](README.md).

## Security notes

- Optional write protection: `PROXYGUARD_TOKEN` + header `X-API-Token`  
- Security headers middleware; CSV upload size/type limits  
- Not multi-tenant SaaS — local/research demo by design  

## License

MIT. Do not use for unauthorized monitoring.

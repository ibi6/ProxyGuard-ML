# Architecture

## Overview

ProxyGuard ML is a **monolithic FastAPI application** that combines:

1. A small **ML pipeline** (synthetic/CSV features → train → evaluate → joblib)
2. A **web console** (Jinja2 + static JS) for demos
3. **SQLite** for train tasks, predict logs, and settings

It is intentionally single-process and local-first. Default data is **synthetic**.

## Layers

```text
┌─────────────────────────────────────────────┐
│ Presentation  templates/ + static/css|js    │
├─────────────────────────────────────────────┤
│ HTTP API      app/api/*  (thin adapters)    │
├─────────────────────────────────────────────┤
│ Services      app/services/* (orchestration)│
├─────────────────────────────────────────────┤
│ ML core       app/ml/*   (pure-ish logic)   │
├─────────────────────────────────────────────┤
│ Persistence   CSV/joblib/JSON + SQLite      │
└─────────────────────────────────────────────┘
```

| Package | Responsibility |
|---------|----------------|
| `app/api` | Request validation, status codes, USE_MOCK switch |
| `app/services` | Business flow, threads, DB rows |
| `app/ml` | Feature schema, models, train/eval/predict |
| `app/db.py` | SQLite schema + connection helper |
| `app/security.py` | Optional API token for write routes |
| `app/middleware.py` | Access log + security headers |

## Request flow (train)

1. `POST /api/train` validates model names  
2. `TrainService.start` enforces single-flight mutex  
3. Background thread runs `train_all` with progress callbacks  
4. Artifacts: `models/*.joblib`, `reports/metrics.json`, figures  
5. UI polls `GET /api/train/{task_id}`  

## Data contract

- Features: `FEATURE_COLUMNS` (17 dims) in `app/config.py`  
- Labels: `normal_https` | `shadowsocks` | `trojan` | `vmess`  
- CSV upload must include `label` + all feature columns  

## Non-goals

- Live packet capture / PCAP parsing  
- Multi-tenant auth / RBAC  
- Distributed training / GPU serving  

## Extension points

| Goal | Where to plug in |
|------|------------------|
| Real PCAP features | Export 17-D CSV → upload, or add extractor under `app/ml/` |
| Auth | Expand `app/security.py` + session store |
| Queue | Replace thread worker with Celery/RQ later |

# Contributing

Thanks for helping improve ProxyGuard ML.

## Development setup

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
```

Optional lint:

```bash
ruff check app tests scripts
```

Run the console:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Project conventions

| Area | Rule |
|------|------|
| Layout | `api` thin → `services` orchestrate → `ml` pure-ish |
| Features | Always validate with `FEATURE_COLUMNS` |
| Reproducibility | Document seed / noise / n_per_class |
| Honesty | Do not present mock or synthetic metrics as real PCAP results |
| Tests | Add/adjust tests under `tests/` for behavior changes |

## Pull requests

1. Fork + feature branch  
2. Keep PRs focused  
3. `pytest -q` must pass  
4. Fill the PR template  

## Do not commit

- `.env`, tokens, personal absolute paths  
- Generated `data/synthetic`, `models/*.joblib`, `*.db`  
- Thesis personal binaries with PII  

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

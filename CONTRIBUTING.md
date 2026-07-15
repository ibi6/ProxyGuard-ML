# Contributing to ProxyGuard ML

Thanks for your interest in improving this project.

## Development setup

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt
pytest -q
```

Start the demo console:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Project conventions

| Area | Guideline |
|------|-----------|
| Language | Prefer clear English identifiers; Chinese is fine in docs/UI copy |
| Style | Keep modules small: `api` → `services` → `ml` |
| Features | Always validate against `FEATURE_COLUMNS` in `app/config.py` |
| Reproducibility | Default seed is `42`; document any new randomness |
| Tests | Add/adjust tests under `tests/` for behavior changes |
| Data honesty | Do not claim real PCAP capture unless you implement it |

## Pull requests

1. Fork the repo and create a feature branch.
2. Keep PRs focused (one concern per PR).
3. Run `pytest -q` before opening the PR.
4. Fill in the PR template.

## What not to commit

- `.env`, credentials, tokens
- Local absolute paths with personal usernames
- Generated datasets under `data/synthetic/` or `data/uploaded/`
- Trained `models/*.joblib` (unless intentionally versioned and small)
- SQLite DB files (`*.db`)

## Code of conduct

Be respectful. Assume good intent. No harassment or personal attacks.
Harassment-free collaboration is required for all participation.

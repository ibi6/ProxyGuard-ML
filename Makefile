.PHONY: help install dev test run experiment smoke docker-up docker-down clean

PYTHON ?= python
UVICORN ?= uvicorn
HOST ?= 127.0.0.1
PORT ?= 8000

help:
	@echo "ProxyGuard ML — common targets"
	@echo "  make install     install runtime deps"
	@echo "  make dev         install runtime + test deps"
	@echo "  make test        run pytest"
	@echo "  make run         start FastAPI console"
	@echo "  make experiment  offline full experiment (n=1000)"
	@echo "  make smoke       tiny offline smoke train"
	@echo "  make docker-up   build & start compose stack"
	@echo "  make docker-down stop compose stack"
	@echo "  make clean       remove caches / local db"

install:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -r requirements.txt

dev: install
	$(PYTHON) -m pip install httpx pytest

test:
	$(PYTHON) -m pytest -q

run:
	$(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload

experiment:
	$(PYTHON) scripts/run_experiments.py --n-per-class 1000 --seed 42

smoke:
	$(PYTHON) scripts/run_experiments.py --n-per-class 200 --seed 42 --models decision_tree,random_forest

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	-$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	-rm -f app/proxyguard.db .coverage
	@echo "cleaned"

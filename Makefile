.PHONY: help install dev test lint run experiment smoke docker-up docker-down clean

PYTHON ?= python
UVICORN ?= uvicorn
HOST ?= 127.0.0.1
PORT ?= 8000

help:
	@echo "ProxyGuard ML"
	@echo "  make install     runtime deps"
	@echo "  make dev         runtime + ruff"
	@echo "  make lint        ruff + compileall"
	@echo "  make test        pytest"
	@echo "  make run         uvicorn :$(PORT)"
	@echo "  make experiment  offline n=800"
	@echo "  make smoke       small train"
	@echo "  make docker-up   compose up"
	@echo "  make docker-down compose down"
	@echo "  make clean       caches / local db"

install:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -r requirements.txt

dev: install
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check app tests scripts
	$(PYTHON) -m compileall -q app scripts tests

test:
	$(PYTHON) -m pytest -q

run:
	$(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload

experiment:
	$(PYTHON) scripts/run_experiments.py --n-per-class 800 --seed 42 --noise 0.85

smoke:
	$(PYTHON) scripts/run_experiments.py --n-per-class 200 --seed 42 --models decision_tree,random_forest

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	-$(PYTHON) -c "import pathlib,shutil;[shutil.rmtree(p,True) for p in pathlib.Path('.').rglob('__pycache__')]"
	-rm -f app/proxyguard.db data/proxyguard.db .coverage
	@echo cleaned

# triage4-bird — common developer entry points.

PYTHON ?= python
PIP    ?= pip

PKG      := triage4_bird
TESTS    := tests

.PHONY: help install install-dev install-ui test lint mypy qa demo ui ui-html web-ui-install web-ui-dev web-ui-build clean

help:
	@awk 'BEGIN{FS=":.*##"; printf "usage: make <target>\n\ntargets:\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:              ## Install the package (no dev extras)
	$(PIP) install -e .

install-dev:          ## Install with pytest + ruff + mypy
	$(PIP) install -e '.[dev]'
	$(PIP) install ruff mypy

install-ui:           ## Install with the [ui] extra (FastAPI + uvicorn + httpx)
	$(PIP) install -e '.[dev,ui]'
	$(PIP) install ruff mypy

test:                 ## Run the pytest suite
	$(PYTHON) -m pytest -q

lint:                 ## ruff check
	ruff check $(PKG) $(TESTS)

mypy:                 ## mypy --ignore-missing-imports
	$(PYTHON) -m mypy --ignore-missing-imports $(PKG)

qa: lint mypy test    ## All quality gates (CI-equivalent)

demo:                 ## Run a station-pass avian-health demo
	$(PYTHON) -m triage4_bird.sim.demo_runner

ui:                   ## Run the FastAPI dashboard on http://127.0.0.1:8000
	$(PYTHON) -m uvicorn triage4_bird.ui.dashboard_api:app --reload

ui-html:              ## Print the offline HTML snapshot to stdout
	$(PYTHON) -c "from triage4_bird.ui.dashboard_api import export_html; print(export_html())"

web-ui-install:       ## npm install (one time, requires Node.js)
	cd web_ui && npm install

web-ui-dev:           ## Run the React/Vite frontend on http://localhost:5173
	cd web_ui && npm run dev

web-ui-build:         ## Production build → web_ui/dist/
	cd web_ui && npm run build

clean:                ## Remove caches + build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

# triage4-farm — common developer entry points. Mirrors the
# Makefile idioms of triage4-fit and triage4.

PYTHON ?= python
PIP    ?= pip

PKG      := triage4_farm
TESTS    := tests

.PHONY: help install install-dev test lint mypy qa demo clean

help:
	@awk 'BEGIN{FS=":.*##"; printf "usage: make <target>\n\ntargets:\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:              ## Install the package (no dev extras)
	$(PIP) install -e .

install-dev:          ## Install with pytest + ruff + mypy
	$(PIP) install -e '.[dev]'
	$(PIP) install ruff mypy

test:                 ## Run the pytest suite
	$(PYTHON) -m pytest -q

lint:                 ## ruff check
	ruff check $(PKG) $(TESTS)

mypy:                 ## mypy --ignore-missing-imports
	$(PYTHON) -m mypy --ignore-missing-imports $(PKG)

qa: lint mypy test    ## All quality gates (CI-equivalent)

demo:                 ## Run a one-herd welfare-screening demo
	$(PYTHON) -c "from triage4_farm.sim.synthetic_herd import demo_herd; from triage4_farm.welfare_check.welfare_engine import WelfareCheckEngine; herd = demo_herd(n_animals=6, n_lame=2); report = WelfareCheckEngine().review(herd); print(report.as_text())"

clean:                ## Remove caches + build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

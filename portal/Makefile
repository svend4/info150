# portal — cross-sibling coordination layer.

PYTHON ?= python
PIP    ?= pip

PKG      := portal
TESTS    := tests

.PHONY: help install install-dev test lint mypy qa demo clean

help:
	@awk 'BEGIN{FS=":.*##"; printf "usage: make <target>\n\ntargets:\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:              ## Install the package
	$(PIP) install -e .

install-dev:          ## Install with pytest + ruff + mypy
	$(PIP) install -e '.[dev]'
	$(PIP) install ruff mypy

test:                 ## Run the pytest suite
	$(PYTHON) -m pytest -q

lint:                 ## ruff check
	ruff check $(PKG) $(TESTS)

mypy:                 ## mypy --strict on the package
	$(PYTHON) -m mypy --ignore-missing-imports --strict $(PKG)

qa: lint mypy test    ## All quality gates (CI-equivalent)

demo:                 ## Cross-sibling smoke (requires pilot siblings installed)
	$(PYTHON) -m portal.cli demo

clean:                ## Remove caches + build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

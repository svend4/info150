# triage4-fit — common developer entry points.
#
# Mirrors triage4/Makefile's idioms: self-documenting via `make
# help`, explicit dev / quality / demo targets, no shell-specific
# magic.

PYTHON ?= python
PIP    ?= pip

PKG      := triage4_fit
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

demo:                 ## Run a one-session coaching demo
	$(PYTHON) -c "from triage4_fit.sim.synthetic_session import demo_session; from triage4_fit.form_check.rapid_form_engine import RapidFormEngine; sess = demo_session('squat', rep_count=5, asymmetry_severity=0.35); result = RapidFormEngine().review(sess); print(result.as_text())"

clean:                ## Remove caches + build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

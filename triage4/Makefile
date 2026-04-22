# triage4 — common developer entry points.
#
# Every target works from the project root (`cd triage4/`). Targets
# that need optional tooling (mutmut, cyclonedx-py) self-check and
# point at the extras install.
#
# Run `make help` to list targets.

PYTHON ?= python
PIP    ?= pip

PKG       := triage4
TESTS     := tests
EXAMPLES  := examples
SCRIPTS   := scripts
IMAGE     := triage4:0.1.0

.PHONY: help install install-dev install-mutation \
        test test-fast lint mypy claims-lint qa \
        benchmark benchmark-json \
        mutation mutation-quick \
        sbom \
        demo-quick demo-crdt demo-twin demo-counterfactual demo-marker demo-uav \
        docker-build docker-run docker-compose-up docker-compose-down \
        clean

help:
	@awk 'BEGIN{FS=":.*##"; printf "usage: make <target>\n\ntargets:\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# -- installation -----------------------------------------------------

install:              ## Install triage4 core (no dev extras)
	$(PIP) install -e .

install-dev:          ## Install triage4 with dev tooling (pytest + ruff + mypy)
	$(PIP) install -e '.[dev]'
	$(PIP) install ruff mypy httpx

install-mutation:     ## Install mutation-testing extras
	$(PIP) install -e '.[dev,mutation]'

# -- quality gates ---------------------------------------------------

test:                 ## Run the full pytest suite
	$(PYTHON) -m pytest -q

test-fast:            ## Stop on first failure; show short tracebacks
	$(PYTHON) -m pytest -x --tb=short

lint:                 ## ruff check
	ruff check $(PKG) $(TESTS) $(EXAMPLES) $(SCRIPTS)

mypy:                 ## mypy --ignore-missing-imports
	$(PYTHON) -m mypy --ignore-missing-imports $(PKG)

claims-lint:          ## Scan user-facing copy for regulatory-framing claims
	$(PYTHON) $(SCRIPTS)/claims_lint.py

qa: lint mypy claims-lint test ## All quality gates (CI-equivalent)

# -- demos + benchmarks ----------------------------------------------

benchmark:            ## Run the full pipeline benchmark (text)
	$(PYTHON) $(EXAMPLES)/full_pipeline_benchmark.py

benchmark-json:       ## Run the benchmark, emit JSON scorecard
	$(PYTHON) $(EXAMPLES)/full_pipeline_benchmark.py --json benchmark.json

demo-quick:           ## One-casualty rapid triage
	$(PYTHON) $(EXAMPLES)/quick_triage.py

demo-twin:            ## Bayesian patient twin particle filter
	$(PYTHON) $(EXAMPLES)/bayesian_twin_demo.py

demo-crdt:            ## 3-medic denied-comms CRDT sync
	$(PYTHON) $(EXAMPLES)/crdt_sync_demo.py

demo-counterfactual:  ## Retrospective counterfactual replay
	$(PYTHON) $(EXAMPLES)/counterfactual_replay.py

demo-marker:          ## Steganographic marker handoff (encode + tamper test)
	$(PYTHON) $(EXAMPLES)/marker_handoff_demo.py

demo-uav:             ## UAV waypoint routing
	$(PYTHON) $(EXAMPLES)/uav_waypoint_demo.py

demo-multi:           ## Multi-platform coordination (UAV + Spot + ROS2)
	$(PYTHON) $(EXAMPLES)/multi_platform_demo.py

demo-calibration:     ## Grid-search calibration walkthrough
	$(PYTHON) $(EXAMPLES)/calibration_walkthrough.py

demo-replay:          ## Mission timeline replay with priority revision
	$(PYTHON) $(EXAMPLES)/mission_replay_demo.py

stress:               ## Scaling + memory stress benchmark (10 / 100 / 500)
	$(PYTHON) $(EXAMPLES)/stress_benchmark.py

stress-big:           ## Stress benchmark at 100 / 1000 / 5000 casualties
	$(PYTHON) $(EXAMPLES)/stress_benchmark.py --sizes 100 1000 5000

# -- mutation testing (opt-in, slow) --------------------------------

mutation:             ## Run mutmut against the triage-critical scope
	@command -v mutmut >/dev/null || (echo "error: mutmut missing. make install-mutation"; exit 2)
	./$(SCRIPTS)/run_mutation.sh

mutation-quick:       ## Mutation-test score_fusion only (~1 min)
	@command -v mutmut >/dev/null || (echo "error: mutmut missing. make install-mutation"; exit 2)
	./$(SCRIPTS)/run_mutation.sh --quick

# -- supply-chain --------------------------------------------------

sbom:                 ## Generate a CycloneDX SBOM at ./sbom.json
	@command -v cyclonedx-py >/dev/null || (echo "error: cyclonedx-py missing. pip install cyclonedx-bom"; exit 2)
	$(PYTHON) $(SCRIPTS)/generate_sbom.py

# -- docker --------------------------------------------------------

docker-build:         ## Build the triage4 slim image
	docker build -t $(IMAGE) .

docker-run:           ## Run the image on port 8000
	docker run --rm -p 8000:8000 $(IMAGE)

docker-compose-up:    ## Bring up docker-compose stack
	docker compose up -d

docker-compose-down:  ## Tear down docker-compose stack
	docker compose down

# -- housekeeping --------------------------------------------------

clean:                ## Remove caches + build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache .mutmut-cache \
	       build dist *.egg-info benchmark.json sbom.json
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

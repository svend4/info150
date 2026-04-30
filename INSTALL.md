# INSTALL — detailed install guide for all 17 packages

Step-by-step install instructions for the entire `info150` monorepo —
every individual package, plus the optional Docker / Web UI / system
dependencies. The root [`README.md`](README.md) has the short version;
this file is the deep reference.

## Table of contents

- [Prerequisites](#prerequisites)
- [Clone the repository](#clone-the-repository)
- [Per-package install — uniform shape](#per-package-install--uniform-shape)
- [Detailed walkthrough — flagship `triage4/`](#detailed-walkthrough--flagship-triage4)
- [Detailed walkthrough — `biocore/`](#detailed-walkthrough--biocore)
- [Detailed walkthrough — `portal/`](#detailed-walkthrough--portal)
- [Detailed walkthrough — the 14 siblings](#detailed-walkthrough--the-14-siblings)
- [Full monorepo install in one shot](#full-monorepo-install-in-one-shot)
- [Docker — flagship only](#docker--flagship-only)
- [Web UI — flagship only](#web-ui--flagship-only)
- [Troubleshooting](#troubleshooting)
- [Uninstall / clean](#uninstall--clean)

---

## Prerequisites

| Tool        | Version | Required for                                           |
|-------------|---------|--------------------------------------------------------|
| Python      | 3.11+   | every package — pinned in each `pyproject.toml`        |
| pip         | 23+     | bundled with Python; upgrade if older                  |
| git         | 2.30+   | clone + branch operations                              |
| GNU make    | any     | every `make install-dev` / `make qa` / `make demo`     |
| Docker      | 24+     | optional — only for `triage4/`'s slim image            |
| docker-compose | v2   | optional — for `make docker-compose-up`                |
| Node.js     | 18+     | optional — only for `triage4/web_ui/` (React + Vite)   |
| npm         | 9+      | optional — only for the web UI                         |

Linux + macOS are tested. Windows works through WSL2; native Windows
PowerShell may need path adjustments in some Make targets.

Verify your toolchain:

```bash
python --version    # ≥ 3.11
git --version       # ≥ 2.30
make --version
docker --version    # optional
node --version      # optional
```

---

## Clone the repository

```bash
git clone https://github.com/svend4/info150.git
cd info150
```

Default branch is `main`. The active development branch as of this
writing is `claude/analyze-documents-structure-Ik1KX`:

```bash
git fetch origin
git checkout claude/analyze-documents-structure-Ik1KX
```

(Optional) Create a Python virtual environment for the whole monorepo:

```bash
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\Activate.ps1       # Windows PowerShell
```

A single venv shared across all 17 packages works fine — every
sibling's `pyproject.toml` is independently resolvable and there are no
cross-sibling dependency conflicts.

---

## Per-package install — uniform shape

Every package follows the same three-step ritual:

```bash
cd <package>
make install-dev      # pip install -e '.[dev]' + extra dev tools
make qa               # ruff + mypy + pytest (~3 s)
make demo             # package-specific smoke (where applicable)
```

There are exactly two exceptions to "uniform":

1. **`triage4/` (flagship)** — `make install-dev` additionally installs
   `httpx` (FastAPI test client). `make demo` is replaced by
   `make benchmark`.
2. **`biocore/`** — has no `make demo` (utility library, no demo entry
   point).

Everything else is sibling-shaped.

---

## Detailed walkthrough — flagship `triage4/`

The most feature-rich package: 130 modules, 759 tests, 5 demo scripts,
FastAPI dashboard, web UI, Docker image.

```bash
cd info150/triage4

# Optional but recommended — local venv
python -m venv .venv && source .venv/bin/activate

# Install + test
make install-dev      # pip install -e '.[dev]' + ruff + mypy + httpx
make qa               # ruff + mypy + claims-lint + pytest (~3 s)

# Full pipeline benchmark on 8 fixture casualties
make benchmark
# or directly:
python examples/full_pipeline_benchmark.py

# FastAPI dashboard (live)
uvicorn triage4.ui.dashboard_api:app --reload
# then: curl http://localhost:8000/health

# All 30+ make targets
make help
```

Key demos (each runs in seconds, no external dependencies):

| Make target           | What it shows                                       |
|-----------------------|-----------------------------------------------------|
| `make demo-crdt`      | denied-comms CRDT sync, 3 medics                    |
| `make demo-marker`    | offline marker codec + tampered/expired rollback    |
| `make demo-multi`     | multi-platform orchestrator: UAV + Spot + ROS2      |
| `make demo-calibration` | grid-search calibration walkthrough               |
| `make demo-replay`    | mission timeline replay                             |
| `make stress`         | scaling benchmark (10 / 100 / 500 casualties)       |

Mutation testing (opt-in, ~1 minute):

```bash
make install-mutation  # pip install -e '.[dev,mutation]'
make mutation-quick
```

---

## Detailed walkthrough — `biocore/`

Shared narrow utility layer (frozen scope). Five modules: `seeds`,
`coords`, `text_guards`, `sms`, `fusion`. Pure stdlib, zero runtime
dependencies.

```bash
cd info150/biocore
make install-dev       # pip install -e '.[dev]' + ruff + mypy
make qa                # ruff + mypy --strict + pytest (78 tests)
# No `make demo` — biocore is a library.
```

Other packages depend on biocore via `pip install -e ../biocore` (the
CI workflow does this implicitly). To install biocore as a dependency
of, for instance, `triage4-fish`:

```bash
pip install -e biocore/
cd triage4-fish && make install-dev
```

---

## Detailed walkthrough — `portal/`

Read-only cross-sibling coordination layer (nautilus-style
"compatibility, not merger"). 75 tests, mypy `--strict` clean.

```bash
cd info150/portal
make install-dev
make qa
```

The portal depends on biocore + on the three pilot siblings
(`triage4-fish`, `triage4-bird`, `triage4-wild`) for end-to-end demos:

```bash
pip install -e biocore/
pip install -e triage4-fish/ triage4-bird/ triage4-wild/
cd portal
python -m portal.cli demo     # cross-sibling bridge discovery (when impl lands)
```

Adapter participation is voluntary; siblings without
`portal_adapter.py` are simply invisible to the portal.

---

## Detailed walkthrough — the 14 siblings

All 14 follow exactly the same shape. Pick the one matching your
domain:

| #  | Package                       | Domain                              |
|----|-------------------------------|-------------------------------------|
| 01 | `triage4-wild/`               | wildlife terrestrial                |
| 02 | `triage4-bird/`               | wildlife avian                      |
| 03 | `triage4-fish/`               | wildlife aquatic / aquaculture      |
| 04 | `triage4-fit/`                | fitness / wellness                  |
| 05 | `triage4-clinic/`             | telemedicine pre-screening          |
| 06 | `triage4-home/`               | elderly home care                   |
| 07 | `triage4-site/`               | industrial safety                   |
| 08 | `triage4-pet/`                | veterinary clinic                   |
| 09 | `triage4-rescue/`             | disaster response (v13 pilot here)  |
| 10 | `triage4-farm/`               | livestock / agtech                  |
| 11 | `triage4-aqua/`               | pool / beach safety                 |
| 12 | `triage4-sport/`              | sports performance                  |
| 13 | `triage4-drive/`              | driver monitoring / fleet           |
| 14 | `triage4-crowd/`              | crowd safety                        |

For each, the install steps are identical:

```bash
cd info150/triage4-<sibling>
make install-dev      # pip install -e '.[dev]' + ruff + mypy
make qa               # ruff + mypy + pytest
make demo             # one-step domain demo
```

`make demo` for each sibling produces a short stdout report
demonstrating the full pipeline (synthetic data → signatures → engine
→ alert/report). Read each sibling's `README.md` for domain context.

### Siblings that depend on biocore

Three siblings already adopt the biocore tier-1 helpers and therefore
need biocore installed before their own `make install-dev`:

```bash
pip install -e biocore/
```

The siblings:

- `triage4-wild` — uses `biocore.coords`, `biocore.seeds`,
  `biocore.text_guards`, `biocore.sms`.
- `triage4-bird` — same set.
- `triage4-fish` — uses everything above + `biocore.fusion` (tier-2).

The other 11 siblings do not yet depend on biocore. Their
`pyproject.toml` will tell you which version of biocore (if any) is
required.

### Sibling with the v13 multiuser pilot

`triage4-rescue` ships a pilot adoption of v13 ideas under
`triage4_rescue/multiuser/` — sessions, RBAC, audit log (in-memory or
opt-in SQLite), async jobs. No additional deps; it's all stdlib.

```bash
cd info150/triage4-rescue
make install-dev
make qa               # 134 tests
make demo             # one-incident triage demo (multiuser is library only)
```

Try the multiuser API in a Python REPL:

```python
from triage4_rescue.multiuser import (
    SessionManager, PolicyEngine, AuditLog, AsyncJobQueue,
)
sm = SessionManager()
sm.create_user("alice", role="dispatcher")
sess = sm.create_session("alice")

pe = PolicyEngine()
pe.require(sess.role, "incident:log")     # passes
pe.require(sess.role, "users:mutate")     # PermissionError

log = AuditLog()                          # in-memory; pass db_path= for SQLite
log.append("incident:log", actor_user_id="alice", actor_role="dispatcher",
           target_id="INC-1", payload={"summary": "structure fire"})
print(log.list())
```

---

## Full monorepo install in one shot

To install + test every package in dependency order:

```bash
cd info150

# Activate venv if you haven't
source .venv/bin/activate

# 1. Shared utility layer first (other packages may depend on it)
( cd biocore && make install-dev && make qa )

# 2. Flagship + 14 siblings (parallel-safe; serial here for clarity)
for pkg in triage4 triage4-*; do
  ( cd "$pkg" && make install-dev && make qa ) || { echo "FAIL: $pkg"; break; }
done

# 3. Cross-sibling coordination layer
( cd portal && make install-dev && make qa )
```

Total wall-clock time: ~2 minutes on a modern laptop (most of which is
pip resolving + downloading wheels; the actual test runs are <1 s
each).

This mirrors `.github/workflows/qa.yml` — the CI matrix runs each
package in parallel.

---

## Docker — flagship only

Only `triage4/` ships a Docker image. The 14 siblings + biocore +
portal are libraries, not services.

```bash
cd info150/triage4

# Build the slim image (< 200 MB)
make docker-build              # docker build -t triage4:0.1.0 .

# Run standalone
make docker-run                # docker run --rm -p 8000:8000 triage4:0.1.0
curl http://localhost:8000/health

# Or via docker-compose (auto-restart, healthcheck, hardening)
make docker-compose-up         # docker compose up -d
curl http://localhost:8000/health
make docker-compose-down       # docker compose down
```

The compose stack also has an optional **edge profile** with an nginx
TLS reverse-proxy (port 8443):

```bash
# 1. Drop your TLS certs into triage4/configs/ first
# 2. Configure bearer auth in triage4/configs/nginx.conf
docker compose --profile edge up -d
```

Three deployment profiles (container / systemd / edge) are documented
in [`triage4/docs/DEPLOYMENT.md`](triage4/docs/DEPLOYMENT.md).

Runtime configuration via env vars:

| Variable             | Default                          | Purpose                          |
|----------------------|----------------------------------|----------------------------------|
| `TRIAGE4_CONFIG`     | `/app/configs/production.yaml`   | Selects sim/runtime config       |
| `TRIAGE4_LOG_LEVEL`  | `info`                           | `debug` / `info` / `warning`     |

---

## Web UI — flagship only

React + Vite dashboard living under `triage4/web_ui/`.

```bash
cd info150/triage4/web_ui
npm install
npm run dev        # http://localhost:5173
```

Production build:

```bash
npm run build      # output: web_ui/dist/
npm run preview    # serves dist/ for sanity-checking
```

The web UI talks to the FastAPI dashboard (`uvicorn triage4.ui.dashboard_api:app`).
Run both in two terminals.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'httpx'` in flagship tests

The flagship's `[dev]` extras don't include `httpx` — it's installed
separately by `make install-dev`. If you ran `pip install -e '.[dev]'`
manually instead of `make install-dev`, run:

```bash
pip install httpx
```

### `mypy --strict` complaints in `biocore/` or `portal/`

These two packages run mypy in strict mode. Plain `--ignore-missing-imports`
mypy will pass; `make qa` enforces strict. If your edit fails strict
mypy, either tighten the annotation or downgrade locally with `make mypy`
(no `qa`) until ready.

### Sibling tests fail with `ModuleNotFoundError: biocore`

The three biocore-adopting siblings (`triage4-wild`, `triage4-bird`,
`triage4-fish`) need biocore installed first:

```bash
pip install -e biocore/
```

### `make demo` fails with `ImportError: numpy`

Most siblings declare `numpy>=1.26`. If `pip install -e '.[dev]'`
didn't pick it up, install manually:

```bash
pip install 'numpy>=1.26'
```

### Docker image fails to start with permission errors

The compose stack uses `read_only: true` + `cap_drop: ALL`. If you
need to debug, comment those lines out in `triage4/docker-compose.yml`
temporarily — but never commit that change.

### Flagship `make claims-lint` fires unexpectedly

Edit `scripts/claims_lint.py` to see the forbidden vocabulary. Fix the
text; do not bypass the linter — see `triage4/docs/REGULATORY.md §9`
for why claims discipline is enforced.

---

## Uninstall / clean

Per package:

```bash
cd <package>
make clean              # removes .pytest_cache, .mypy_cache, .ruff_cache, build artefacts
pip uninstall -y <package-name>
```

Whole monorepo:

```bash
cd info150
for pkg in biocore portal triage4 triage4-*; do
  ( cd "$pkg" && make clean ) || true
  pip uninstall -y "$(basename "$pkg")" 2>/dev/null || true
done
deactivate            # exit venv
rm -rf .venv          # delete venv if you want a fully clean slate
```

Docker artefacts:

```bash
cd info150/triage4
make docker-compose-down
docker rmi triage4:0.1.0
```

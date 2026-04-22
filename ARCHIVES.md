# Frozen archives in this repo

Two non-code artefacts live at the repo root. Neither is consumed
by the triage4 build or tests — they are **historical /
conceptual reference material**. Listed here so nobody mistakes
them for deliverables or tries to integrate them by accident.

## 1. `Branch · Branch · Branch · Обзор проекта svend4_meta2.{md,txt,json}`

Three formats of the same ChatGPT conversation that seeded the
project.

| Format | Size | Role |
|---|---|---|
| `.json` | 477 KB | 96 messages, ids, timestamps, role markers. Canonical. |
| `.md`   | 429 KB | Markdown rendering of the same conversation. |
| `.txt`  | 396 KB | Plain-text rendering of the same conversation. |

### What it contains

- **Date:** 2026-04-01 13:51 → 21:03 (~7 hours).
- **Participants:** one human user + ChatGPT.
- **First half (msgs 0-50):** analysis of three sibling repos
  (`svend4/meta2`, `svend4/infom`, `svend4/in4n`), discussion of
  DARPA Triage Challenge Event 3 (prompted by a YouTube video
  segment at 9:38 — screenshots referenced but stripped out of
  the export), construction of the K3 fractal matrix
  (1.1/1.2/1.3 × 2.1/2.2/2.3 × 3.1/3.2/3.3), blueprint for
  triage4.
- **Second half (msgs 51-95):** a parallel evolution trajectory
  **v1 → v13** of a different triage4 variant (see section 2).
- **Images:** msgs 18/19/20 originally held screenshots (YouTube
  frames). URLs were stripped on export; only alt-text context
  in surrounding messages remains.

### Relationship to the current codebase

- The K3 matrix + the initial blueprint from the first half **is
  the conceptual foundation** of everything under `triage4/`.
- The v6 → v13 progression from the second half **is not** —
  see section 2.

### Why it's kept

- Provenance: a reader can trace every architectural decision
  back to a specific message in this log.
- Methodological references (Larrey, Eulerian VM, DTW, etc.)
  were mined from it; see `triage4/docs/FURTHER_READING.md`.

### Why it's NOT read by the build

- Plain-text conversation log, not structured data.
- Mining is one-shot, already done; the extracted facts live in
  the triage4 docs.

## 2. `triage4_repo_v13.zip`

A 530 KB zip produced by the ChatGPT conversation in section 1,
capturing its **v13 evolution target** — an enterprise / SaaS
variant of triage4. Checked in on main at commit `9e0bbd9`
(2026-04-22).

### What's inside

- **84 Python modules, ~4,500 LOC** — about one-third the size
  of our current `triage4/`.
- **12 short Markdown docs** (README, API, ARCHITECTURE,
  ROADMAP, BOOTSTRAP, DATA_MODEL, SCENARIOS, SETUP, CODE_PACK,
  MASTER_INDEX, CONTRIBUTING).
- **16 repository modules over SQLite** — scenarios, casualties,
  users, sessions, policies, audit, workspaces, notifications,
  presets, jobs, baselines.
- **Auth layer** — `session_manager.py`, `permissions.py`,
  `policy_engine.py`.
- **Jobs layer** — `job_manager.py`, `async_queue.py`,
  `worker_loop.py`, `worker_process.py`.
- **Schemas** — `scenario_schema.py`, `user_schema.py`.
- **17 React pages** under `web_ui/src/pages/` — Sessions,
  Presets, Jobs, Diffs, Workspace, WorkspaceHistory, Analytics,
  Notifications, PolicyProfiles, Audit, Events, ScenarioEditor,
  CasualtyPage, MapPage, ReplayPage, WorldStatePage,
  CoordinationPage.
- **15 `test_v{N}_features.py`** files (N = 1..12) — one test
  file per feature version.
- **Pre-computed data** — `triage4.sqlite` (5.5 MB, binary DB),
  `data/scenarios/*.json`, `data/replay_sessions/*.json`,
  `data/baseline_runs.json`, `data/notification_rules/*.json`,
  `data/digest_presets/*.json`.
- **Checked-in `__pycache__` / .pyc** — 30+ compiled bytecode
  files bundled in the archive (not stripped by the packager).

### Relationship to the current `triage4/`

**Alternative, incompatible architecture.** The two codebases
share a name and some early ideas, but the divergence is
structural:

| Axis | Our `triage4/` | `triage4_repo_v13.zip` |
|---|---|---|
| Framing | Research / decision-support / DARPA | Multi-user SaaS platform |
| Modules | 130 | 84 |
| LOC | ~12,000+ | ~4,500 |
| Tests | 759 (invariant regression) | ~45 (per-version features) |
| Persistence | in-memory (stateless by design) | SQLite (5.5 MB checked in) |
| Auth | none (RISK SEC-003 forbids PHI) | sessions + role-based + policy engine |
| Regulatory docs | REGULATORY + SAFETY_CASE + RISK_REGISTER + 10 more | README + API + ROADMAP only |
| K3 matrix | all 9 cells implemented | not present |
| DARPA gate evaluators | 5 + HMT + counterfactual | not present |
| Platform bridges | SITL/ROS2/Tello/MAVLink/Spot/WebSocket | not present |
| Property / mutation testing | yes | no |
| Web UI | minimal scaffold (3 pages) | 17 SaaS pages |

### Why importing from v13 is not recommended

- v13's auth / sessions / workspaces / notifications layer
  **contradicts** the decision-support posture documented in
  `triage4/docs/REGULATORY.md §9` (claims discipline) and
  `triage4/docs/RISK_REGISTER.md` rows **SEC-003** (PHI leakage)
  and **DATA-005** (no PHI in repo).
- v13's `data/triage4.sqlite` contains pre-computed casualty
  records. Even if synthetic, merging that blob would
  strain the "no patient-like data in the repo" commitment.
- v13 has no `ruff` / `mypy` / `claims-lint` / regulatory
  documentation. Merging would regress every quality gate the
  current codebase enforces.
- v13's `triage4/dynamic/dynamic_body_graph.py` overlaps with
  our `state_graph/skeletal_graph.py` (K3-1.3), but uses a
  region-centric rather than joint-centric decomposition. Our
  implementation is strictly more clinically defensible
  (explicit L/R asymmetry pairs, wound-intensity slope, motion
  score clipped to [0, 1]).

### What might be worth extracting later

A small amount of code is technically reusable if the project
ever needs the corresponding capability:

- `triage4/analytics/diffing.py` (~40 LOC) — `deep_diff(left,
  right)` recursive dict/list/scalar comparison. Could underpin
  a baseline-comparison CI report. **Easier to rewrite from
  scratch than port**, given v13's unrelated surrounding
  conventions.
- `triage4/analytics/timeline.py` (~20 LOC) — world-state /
  casualty timeline builder. **Already covered** by our
  `TimelineStore` + `ReplayEngine`.
- `triage4/analytics/comparison.py` (~40 LOC) — per-field delta
  between two world-states. **Already covered** by our
  counterfactual evaluator.

**No extraction is planned.** This list exists only so a future
contributor doesn't have to re-audit the archive from scratch.

### Why the zip is kept

- It is the **canonical evidence** of the v6 → v13 trajectory
  described in the ChatGPT conversation log.
- 530 KB is trivial on-disk cost.
- Deleting it removes the ability to re-audit the path-not-taken
  without re-running the original conversation.

### Safety caveat

- **Do not extract** `triage4_repo_v13/data/triage4.sqlite` to
  a working tree and commit it — the synthetic casualty rows
  resemble PHI enough to trip the "no patient-like data"
  discipline.
- **Do not `pip install`** the v13 package. Its module tree
  would shadow our `triage4` namespace and break imports.
- If a future contributor wants to reference v13 code, unzip it
  under `/tmp/` or a sibling directory, not inside this repo.

## Integrity

Both archives are read-only from the triage4 project's
perspective. The current branch's CI, tests, and documentation
do not depend on either one. Removing the archives would not
break any build; they are preserved as reference material only.

Last audit: see `triage4/docs/STATUS.md` for the latest
project-state synthesis.

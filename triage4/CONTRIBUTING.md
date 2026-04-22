# Contributing to triage4

Short, opinionated guide. triage4 is a small research stack; one
maintainer, a handful of contributors. These conventions exist so
the codebase stays coherent without heavyweight process.

## Scope

triage4 is an **autonomous stand-off triage decision-support stack**
for DARPA-Triage-Event-3-class scenarios. PRs are welcome when they:

- fix a bug in existing behaviour,
- close a gap documented in `docs/ROADMAP.md` / `docs/RISK_REGISTER.md`,
- add a test that locks an invariant,
- improve docs without expanding scope.

PRs outside that scope will be closed with a pointer to the roadmap.

## Before you start

1. **Read the safety framing.** `docs/REGULATORY.md`,
   `docs/SAFETY_CASE.md`, `docs/RISK_REGISTER.md`. triage4 is
   decision-support, not a medical device. Every change is held to
   that framing.
2. **Check existing issues / PRs.** Duplicate work is cheap to
   avoid.
3. **Open a small issue before any > 200-line change.** Keeps the
   review loop fast.

## Environment

```bash
git clone <repo> && cd triage4
python -m venv .venv && source .venv/bin/activate
make install-dev
```

Python ≥ 3.11. No GPU, no external SDKs. Optional extras:

- `make install-mutation` — adds mutmut for mutation testing.
- `pip install cyclonedx-bom` — SBOM generation via `make sbom`.

## Workflow

- **Branch naming** — descriptive slug, like `fix/mavlink-frame-swap`
  or `feat/prometheus-metrics`. Avoid `work/` or personal
  namespaces.
- **Commits** — clear, factual subject line (≤ 70 chars), body
  explains *why*. Reference any RISK / ROADMAP ids.
- **One logical change per PR.** A refactor and a feature do not
  share a PR.
- **Rebase, don't merge.** Keep history linear on feature branches.

## Tests

**Every PR must add or update at least one test.** Two exceptions:

- pure-docs PRs;
- deletions that have an explicit RISK_REGISTER / ROADMAP reference
  justifying the removal.

Rules the existing tests follow — please keep to them:

- **Fixed seeds.** No randomness leaks across tests.
- **No sleeps / no timers.** If you need to test timing, inject
  `now_ts` or use `time.time` via a helper.
- **Contracts, not numbers.** Prefer `assert result.ok` over
  `assert result.score == 0.837`. Numeric tests are fine when the
  invariant is the number (e.g. HR MAE bound in `test_gate4_vitals`).
- **One concept per test.** A regression test locks one invariant;
  if it needs three `assert`s, rename it so the docstring explains
  the single claim.

## Local quality gates

```bash
make qa         # ruff + mypy + claims-lint + pytest
make benchmark  # smoke-run the end-to-end pipeline
```

CI runs the same set on Python 3.11 and 3.12. PRs that fail CI will
not be merged.

## Code style

- `ruff` enforces formatting and a curated lint set (config in
  `pyproject.toml` — if there is no config block, ruff defaults are
  what we use).
- `mypy --ignore-missing-imports` on `triage4`. Add type hints on
  new public surface; relax only when the third-party shape can't be
  expressed.
- **Comments.** Default to none. Write one only when the *why* is
  non-obvious. Never narrate the *what* — names already do that.
- **Docstrings.** Module and class docstrings are encouraged; one-
  sentence function docstrings are welcome. Multi-paragraph
  docstrings only on public-surface classes or complex modules.
- **No emojis** in source files unless explicitly requested.

## Claims discipline

`scripts/claims_lint.py` runs in CI. It refuses framing claims
("diagnose", "FDA-cleared", "medical device", "triage4 can treat"  [claims-lint: allow]
patterns). Regulatory discussion files (`REGULATORY.md`,
`RISK_REGISTER.md`, `SAFETY_CASE.md`) are allow-listed.

For a legitimate one-off mention, use the inline marker:

```markdown
<!-- mentions the forbidden word for context -->  [claims-lint: allow]
```

Don't abuse it.

## Safety-critical changes

Modules in the mutmut scope — see `pyproject.toml [tool.mutmut]` —
are triage-critical:

- `triage_reasoning/score_fusion.py`
- `triage_reasoning/rapid_triage.py`
- `triage_reasoning/larrey_baseline.py`
- `triage_reasoning/celegans_net.py`
- `mission_coordination/mission_triage.py`
- `integrations/marker_codec.py`
- `integrations/bridge_health.py`

Changes to these need:

1. A test that would catch the opposite-of-intended behaviour.
2. A one-line note in `CHANGELOG.md` referencing the RISK_REGISTER
   row affected.
3. A run of `make mutation-quick` (or full `make mutation`) locally
   if the change plausibly widens the mutmut survivor set.

## What not to do

- Don't add a runtime dependency without an issue. Core deps are
  `numpy`, `scipy`, `fastapi`, `uvicorn`, `pydantic`, `pyyaml`.
  Everything else is an optional extra.
- Don't disable tests to land a change. Fix the test or open an
  issue explaining why the assertion is wrong.
- Don't add a feature behind a flag "for later". If it isn't
  wired up now, delete it.
- Don't commit generated files (`sbom.json`, `benchmark.json`).
- Don't commit credentials, secrets, or PHI. Ever. Check
  `DEPLOYMENT.md §3` for the env-var slots.

## Issue / PR templates

No formal templates yet. Good issues include:

- what happened vs what you expected,
- a minimal repro,
- Python version + OS,
- relevant RISK_REGISTER id if applicable.

Good PRs include:

- what and why in the commit body,
- linked issue if any,
- mention of the test that locks the change,
- a note on any RISK_REGISTER row moved.

## License

triage4 is MIT. By contributing you agree your work is too. Upstream-
adapted modules keep their original MIT notices — see
`third_party/ATTRIBUTION.md`.

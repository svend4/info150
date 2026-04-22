# info150

Monorepo for the **triage4** project — a simulation-first
autonomous stand-off triage research stack.

The actual code, tests, docs, and deployment artefacts live under
[`triage4/`](triage4/). This top-level directory also carries the
original conceptual drafts the project started from.

## Layout

```
info150/
├── README.md                         # this file
├── triage4/                          # the project proper (see below)
└── Branch · Branch · Branch · Обзор проекта svend4_meta2.{md,txt,json}
                                      # original ChatGPT design log (~12,500 lines)
                                      # inputs to Phases 1–6 scaffolding
```

## triage4 at a glance

- **What:** decision-support pipeline for DARPA Triage Challenge
  Event 3–class scenarios. Takes stand-off sensor observations →
  signatures → triage priority → graph → autonomy → handoff.
- **Status:** 609 tests · 123 modules · CI green · Phases 1–9e
  complete · Phase 12 (regulatory), Phase 10-prep (HW scaffold),
  Phase 13-prep (deployment) done · Levels A–C (gap closures,
  dev UX, docs polish) done. See
  [`triage4/docs/STATUS.md`](triage4/docs/STATUS.md) for the
  honest pros / cons.
- **License:** MIT. See [`triage4/LICENSES/`](triage4/LICENSES/).

## Quickstart

```bash
cd triage4
make install-dev        # pip install -e '.[dev]' + ruff + mypy + httpx
make qa                 # full CI-equivalent sweep (~3 s)
make benchmark          # 8-casualty end-to-end pipeline
make help               # every other target
```

## Entry points in `triage4/`

Start here, in order:

1. [`triage4/README.md`](triage4/README.md) — project quickstart +
   docs index.
2. [`triage4/docs/STATUS.md`](triage4/docs/STATUS.md) — technical
   + conceptual pros / cons, what was built, what's still open.
3. [`triage4/docs/ONE_PAGER.md`](triage4/docs/ONE_PAGER.md) —
   grant-ready one-pager.
4. [`triage4/docs/ARCHITECTURE.md`](triage4/docs/ARCHITECTURE.md)
   — K3 matrix (signal × structure × dynamics, body × meaning ×
   mission) and the fractal recursion across scales.
5. [`triage4/docs/ROADMAP.md`](triage4/docs/ROADMAP.md) — full
   phase-by-phase history.

## Disclaimer

triage4 is **research-grade decision-support software** — not a  [claims-lint: allow]
certified medical device and must not be used as a standalone
source of clinical decisions. It is framed, tested, and documented
as decision support for qualified operators. See
[`triage4/docs/REGULATORY.md`](triage4/docs/REGULATORY.md) and
[`triage4/docs/SAFETY_CASE.md`](triage4/docs/SAFETY_CASE.md).

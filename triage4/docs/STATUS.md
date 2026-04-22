# triage4 — Technical + Conceptual Status

Honest self-assessment of the project as of the current commit on
branch `claude/analyze-documents-structure-Ik1KX`. Not marketing
copy. Intended to be read before a grant submission, a partner
kickoff, or any decision that assumes triage4 is further along than
it is.

## 1. What was built (scope)

- 123 Python modules, 609 tests, CI green on Python 3.11 + 3.12.
- 12 docs (this one makes 13).
- 11 runnable example scripts including a full-pipeline benchmark,
  multi-platform coordination, calibration walkthrough, mission
  replay, stress benchmark, denied-comms CRDT sync, offline
  markers, Bayesian twin, counterfactual replay.
- Containerised (Dockerfile + compose + systemd + nginx template).
- Regulatory framework documented (REGULATORY + SAFETY_CASE +
  RISK_REGISTER, non-binding, pre-clinical).
- 2 RISK_REGISTER gates closed (CLAIM-001 via claims-lint CI,
  CI-002 via mutmut setup).
- 4 hardware-ready PlatformBridge implementations (loopback) +
  skeletons for ROS2 / MAVLink / bosdyn / FastAPI WebSocket real
  backends.
- 1 `MultiPlatformManager` orchestrator.
- Prometheus `/metrics` endpoint (stdlib-only, no
  `prometheus_client` dep).
- SBOM generator (`cyclonedx-py` CLI path + stdlib fallback).
- 9 hypothesis property-based tests (CRDT algebra, marker codec,
  score fusion monotonicity).

## 2. Technical pros

- **No external SDK dependencies at import time.** Every robotics
  SDK (rclpy / pymavlink / bosdyn) is lazy-imported behind a
  `build_*_bridge` factory. `pip install triage4` installs
  numpy + scipy + fastapi + pydantic + pyyaml, nothing else.
  Proven by the end-to-end test that asserts no SDK is in
  `sys.modules` after import.
- **Deterministic pipeline.** Every randomised component uses a
  seeded RNG; tests use fixed seeds; `Bayesian twin` uses 200
  particles with declared seed. The whole 8-casualty benchmark
  is reproducible byte-for-byte.
- **Linear scaling.** Stress benchmark shows the triage hot path
  stays at ~11 µs/casualty and ~280 bytes/casualty at N=5000. No
  hidden O(N²).
- **Property-tested algebra.** CRDT merges are hypothesis-verified
  commutative + idempotent + associative across randomised event
  histories. Marker codec rejects any single-byte flip and any
  wrong secret, verified over ~50 random traces per property.
- **Test-as-specification.** 609 tests lock invariants
  (critical-miss rate = 0 on isolated mortal signs, CRDT
  convergence, multi-platform health gating, etc.) so a change
  that accidentally widens the safety envelope can't land silently.
- **Multi-layer decision framing.** Every triage output carries
  reasons + per-channel confidence + optional grounded summary,
  by construction. No black-box.
- **Mortal-sign override as regression-tested invariant.** The
  Larrey-gap that Phase 9a surfaced cannot re-appear without a
  named test failing.
- **CI gates are real.** Every PR runs ruff + mypy + claims-lint
  + pytest + full benchmark + 9 demo scripts. A broken demo
  fails CI, not silently rots.
- **Regulatory posture is code-adjacent.** Forbidden framings
  ("diagnose", "FDA-cleared", "medical device", product-action
  claims) are blocked by the CI claims-lint. The regulatory
  discussion docs are explicitly allow-listed so they can name
  what they're warning against.

## 3. Technical cons / remaining gaps

- **Real perception is a skeleton.** `YOLODetector` ships as a
  loopback; the `build_ultralytics_detector` factory exists but
  is not CI-tested — there is no real image → detection → pose
  chain on real data. Tagged RISK CAL-002.
- **Platform bridges are loopback-only.** Real rclpy / pymavlink
  / bosdyn paths raise `NotImplementedError`. The wiring is
  well-documented in HARDWARE_INTEGRATION.md; the field-test
  loop is missing.
- **No clinical data yet.** Calibration runs on a 70-case
  synthetic dataset. PhysioNet adapter is in place but no real
  archive has been ingested. Tagged RISK CAL-001. This is the
  single biggest gap between Alpha and credible Beta.
- **3 K3 matrix cells still empty:**
  - 1.3 dynamic skeletal graph (time-evolving body + wound
    morphology);
  - 2.2 conflict resolver (contradictory-evidence reconciliation);
  - 3.3 forecast layer (mission / patient trajectory projection).
- **Mutation testing is configured but not yet run.** The
  opt-in `make mutation` path works; a first full run against
  the 7-module scope has not been scored. Survivor-rate baseline
  is unknown.
- **Web UI is scaffolded, not finished.** React components exist
  (`SemanticZoom`, `InfoPanel`) but pages for mission replay,
  calibration UI, operator override are TBD.
- **Logs are structured-JSON by default but no sink is wired.**
  `DEPLOYMENT.md §5` lists Loki / ELK as "future".
- **SBOM fallback loses SPDX-compliance.** The stdlib fallback
  emits CycloneDX-shaped JSON but without full licence
  normalisation. Real regulatory contexts need `cyclonedx-py`.
- **DeprecationWarnings in `ui/dashboard_api.py`.** FastAPI
  deprecated `@app.on_event("startup")` in favour of lifespan
  handlers. Non-fatal, surface noise in test output.

## 4. Conceptual pros

- **K3 matrix (signal / structure / dynamics × body / meaning /
  mission) is a genuine mental model, not a slide.** Seven of
  nine cells have implementations. Readers can locate any new
  module into exactly one cell.
- **Fractal mission-as-casualty** (Phase 9e) makes the
  same-vocabulary recursion explicit: the mission itself carries
  a 5-channel signature and is triaged like a patient. Small
  code footprint, large conceptual payoff.
- **Decision-support framing is baked in.** The regulatory doc,
  the claims-lint, the Larrey override, the "LLM phrases but does
  not decide" grounding Protocol — all reinforce the same
  boundary: triage4 assists, never replaces, a medic.
- **Larrey 1797 baseline as a living regression test.** 200-year-
  old battlefield rules cross-check every modern classifier
  release. A rule older than electricity is harder to tune away
  in a fit of optimisation.
- **Cross-domain math re-use.** Box-counting / Richardson / CSS /
  chain-code / DTW / rotation-DTW / Fréchet / Hu moments all
  shipped via Phase 6.5 — shape and matching machinery that
  would otherwise need to be written from scratch for triage.
- **Grounded LLM pattern.** The `LLMBackend` Protocol gives any
  LLM provider a plug point without letting it influence triage
  decisions. Clean separation even if nobody attaches an LLM.
- **Denied-comms is a first-class feature.** Three medic tablets
  can sync pairwise with provably commutative merges (CRDT).
  Orthogonally, offline markers let a medic leave a verifiable
  casualty note on the ground when CRDT sync is impossible.
  Two different comms-down stories, both shipped.

## 5. Conceptual cons / remaining gaps

- **"Multiscale fractal triage perception" is implicit, not
  explicit.** The architecture docs describe the K3 matrix but
  don't elevate the *fractal* recursion as the primary mental
  model. Readers miss the unifying thread.
- **Stand-off vs contact vitals taxonomy is scattered.**
  Thermal / Eulerian video / motion / posture are "stand-off";
  HR / RR contact estimators live in `vitals_estimation.py`.
  The vocabulary is consistent but there is no single table that
  lists which module consumes which sensor class.
- **No bibliography.** Eulerian video magnification (MIT
  CSAIL), Larrey 1797, Shannon entropy, CRDT Handbook, Bayesian
  experimental design, MIMIC-III — all cited in scattered
  comments, never consolidated. A `FURTHER_READING.md` would fix
  this in one file.
- **No explicit "Scope & Non-Scope" anchor.** Every doc alludes
  to the decision-support framing; none states it as a
  one-screen set of positive and negative claims. A partner
  reading the ONE_PAGER has to assemble that picture themselves.
- **C.elegans classifier is a one-off.** The "small hand-authored
  fixed-topology network" pattern could extend to other decisions
  (handoff timing, forecast, conflict resolution) but currently
  ships as exactly one 4-6-3 network.
- **"Foveal + peripheral" sensing metaphor.** Active-sensing
  (Phase 9a) picks the next observation by information gain — a
  good biological analogue, but the biological framing is not in
  the docs.

## 6. What still needs external resources

- **Phase 10 proper** — live UAV / quadruped / sensor chain
  integration. ~2 engineer-weeks per platform once a real device
  is available. HARDWARE_INTEGRATION.md holds the playbook.
- **Phase 11** — clinical partnership + IRB approval. Cannot be
  done without a hospital / research-site partner and a
  qualified regulatory consultant. PhysioNet adapter is ready
  for the data side.
- **Phase 13 proper** — production deployment at a specific
  customer site. Config is ready; secrets / TLS / monitoring
  integration is customer-specific.

## 7. Methodological leverage — ideas from the original drafts

The source chat log (`/home/user/info150/Branch · Branch · Branch
· Обзор проекта svend4_meta2.md`, ~12,500 lines) contains several
methodological ideas that went into the K3 design but have **not
yet landed as code**. Most valuable leads:

- **K3-1.3 Dynamic Skeletal Graph** — a time-evolving body graph
  with wound morphology and limb-asymmetry tracking. Current
  implementation is static polygon regions (K3-1.2 only). This
  is the single most articulated-but-unfinished cell.
- **K3-2.2 Conflict Resolver** — reconciles contradictory trauma
  hypotheses via support/conflict edge weighting, rank-order
  voting, and uncertainty quantification. Stub exists in the
  state_graph module; the reasoning layer does not yet consume
  it.
- **K3-3.3 Forecast Layer** — projects casualty trajectory and
  mission escalation into the near future. Timeline storage +
  replay ship in Phase 9c; predictive "what happens if we do
  nothing for 10 minutes" does not.
- **Tangram body-region abstraction** — the body decomposed into
  stable geometric parts. Implemented (`perception/body_regions.py`)
  but the naming / narrative is under-surfaced in the docs.
- **Multi-scale C.elegans classifiers** — the same fixed-topology,
  auditable pattern applied to handoff-timing and conflict-
  resolution, not just priority.
- **Acoustic channel fusion** — `acoustic_signature.py` ships a
  bandpower baseline; a future revision could weight groans and
  wheezes into the hemorrhage-likelihood hypothesis.

Each item is a roadmap candidate, not a shipped feature.

## 8. Bottom line

- **TRL 3–4.** Alpha-grade research software. Every
  correctness-relevant path is tested; every safety-relevant path
  is both tested and documented; no clinical claim is made.
- **Deployment-ready in loopback.** Containerised, sandboxed,
  metrics-scrapable, SBOM-generatable, claims-lint-clean.
- **Blocked on external resources, not on code.** Phases 10 / 11 /
  13 need hardware / clinical partners / customers respectively;
  the scaffold is in place for each.
- **Small conceptual debt** — mostly about surfacing the existing
  framing (fractal / stand-off taxonomy / scope anchor /
  bibliography), not about inventing new ideas.
- **Three K3 cells** represent the only *self-contained* technical
  work left that can be done without external dependencies. All
  three are independently scoped and could be tackled one at a
  time.

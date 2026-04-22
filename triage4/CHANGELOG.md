# Changelog

All notable changes to **triage4** are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com).

Work has been organised by numbered Phases of the roadmap; each Phase
is implemented by one or several commits on the feature branch.

---

## Unreleased / 0.1.0 — branch `claude/analyze-documents-structure-Ik1KX`

### Status analysis + docs polish

- `docs/STATUS.md` — honest technical + conceptual pros / cons,
  what was built, what's still open, what the original drafts
  still have that isn't yet mined. Includes the 3 K3 cells that
  remain as self-contained future work.
- `docs/FURTHER_READING.md` — consolidated bibliography (Larrey,
  Eulerian VM, DTW, CRDT, HMAC, IEC 62304, ISO 14971, hypothesis,
  mutmut, and ~30 more), grouped by triage4 area with module
  cross-references.
- Root `README.md` — replaced the 2-line placeholder with a
  monorepo layout overview, project status line, quickstart, and
  entry-point index pointing into `triage4/`.
- `triage4/README.md` — status block now includes Level B and
  Level C; docs index surfaces STATUS.md and FURTHER_READING.md;
  explicit list of the 3 open K3 cells.
- `docs/ROADMAP.md` — "Open self-contained work — 3 remaining K3
  cells" section added so the only remaining non-external work
  is visible at a glance.

### Level C — Benchmarks + demos + docs refinement

- `examples/stress_benchmark.py` — scaling + memory benchmark with
  per-casualty µs / KB + slope classification. Linear at 5k casualties.
- `examples/multi_platform_demo.py` — `MultiPlatformManager` run with
  UAV + Spot + ROS2 bridges and health-gated dispatch.
- `examples/calibration_walkthrough.py` — end-to-end calibration
  demo on the 70-case realistic dataset.
- `examples/mission_replay_demo.py` — timeline recording + replay
  with mid-mission priority revision.
- `docs/CALIBRATION.md` — what calibration tunes, dataset layout,
  API walkthrough, when to recalibrate, real-data path.
- `docs/EXPLAINABILITY.md` — three explanation layers, LLM grounding
  Protocol, observability, non-goals.
- `Makefile` — `demo-multi`, `demo-calibration`, `demo-replay`,
  `stress`, `stress-big` targets added.
- `.github/workflows/ci.yml` — Level C demos run on every PR.
- `README.md` — new docs indexed under regulatory/safety; demo
  quickstart refreshed.

### Level B — Developer experience polish

- `Makefile` — 24 targets covering install / QA / benchmark / demos /
  mutation / SBOM / Docker / housekeeping. `make help` self-documents.
- `CONTRIBUTING.md` — scope, workflow, test rules (fixed seeds, no
  sleeps, contracts-over-numbers), claims discipline, safety-critical
  change protocol, do-nots.
- `README.md` refresh — status block now lists Phases 1–9e + Level A,
  595→609 tests, Makefile quickstart, expanded docs index with
  regulatory / integration / process groupings.
- `scripts/generate_sbom.py` + `tests/test_generate_sbom.py` —
  CycloneDX JSON SBOM generator with cyclonedx-py CLI path and
  stdlib `importlib.metadata` fallback. 5 tests lock the
  fallback format.
- `tests/test_properties.py` — 9 hypothesis property-based tests
  for CRDT merge algebra (commutative / idempotent / associative),
  marker codec (roundtrip, QR roundtrip, any-single-byte-flip
  rejection, wrong-secret rejection), and score fusion (bleeding-
  monotonicity, unit-interval invariant).
- `integrations/marker_codec.py` — hardened against malformed
  base64 signatures and invalid-range payloads surfaced by the
  property test. Any tampered envelope now raises `InvalidMarker`
  rather than letting `binascii.Error` / `ValueError` escape.
- `pyproject.toml` — adds `hypothesis>=6.100` to `[dev]`.

### Level A — Gap closures (claims-lint, mutation, multi-platform, metrics)

Four discrete items that close tracked gaps from `RISK_REGISTER.md`
and the Phase 10-prep / 13-prep open questions. No new runtime deps.

- `scripts/claims_lint.py` + `tests/test_claims_lint.py` — product-
  claim linter with allowlist and inline opt-out marker. Wired into
  CI (`.github/workflows/ci.yml`). Closes CLAIM-001 gate.
- `pyproject.toml [tool.mutmut]` + `scripts/run_mutation.sh` +
  `docs/MUTATION_TESTING.md` + `tests/test_mutation_config.py` —
  mutation testing scoped to 7 triage-critical modules. Opt-in
  runtime. Closes CI-002 gate.
- `integrations/multi_platform.py` + `tests/test_multi_platform.py`
  — `MultiPlatformManager` orchestrator satisfying `PlatformBridge`,
  with broadcast / targeted publish and health-gated dispatch.
  Addresses HARDWARE_INTEGRATION §7 open question.
- `ui/metrics.py` + `tests/test_metrics.py` + `GET /metrics` on
  dashboard — stdlib-only Prometheus text-format exposition:
  `triage4_casualties_total`, `triage4_handoff_latency_seconds`,
  `triage4_bridge_health`, uptime. Addresses DEPLOYMENT §9 open
  question.

RISK_REGISTER.md:
- CLAIM-001 residual: 4×2=8 → 4×1=4 (no longer a gate).
- CI-002 residual: 3×3=9 → 3×2=6 (no longer a gate).

### Phase 13-prep — Deployment patterns

- `Dockerfile` + `.dockerignore` — slim multi-stage image, runs as
  unprivileged user, includes HEALTHCHECK. Size < 200 MB.
- `docker-compose.yml` — read-only FS, dropped capabilities,
  no-new-privileges, localhost-only port binding, optional nginx
  reverse-proxy profile.
- `deploy/triage4.service` — systemd unit with full sandboxing
  (NoNewPrivileges, ProtectSystem=strict, MemoryDenyWriteExecute,
  SystemCallFilter).
- `configs/production.yaml`, `configs/edge.yaml`, `configs/nginx.conf`
  — three reference deployment profiles with env-var secret slots.
- `docs/DEPLOYMENT.md` — container / systemd / edge profiles, secret
  handling, upgrade / rollback, pre-deployment checklist.
- `tests/test_deployment_artifacts.py` — 19 smoke tests that lock
  the security-relevant flags of every deployment artefact.

### Phase 10-prep — Hardware integration scaffold

- `integrations/bridge_health.py` — `BridgeHealth`,
  `check_bridge_health`, `check_telemetry`, `safe_to_dispatch`.
- Real-backend factory skeletons in `ros2_bridge`, `mavlink_bridge`,
  `spot_bridge`, `websocket_bridge` now carry concrete SDK call
  outlines. Still raise `NotImplementedError`.
- `tests/test_bridges_contract.py` — 29 Protocol-conformance + health-
  check tests plus real-backend factory failure-mode tests.
- `docs/HARDWARE_INTEGRATION.md` — per-platform wiring guide,
  first-flight checklist, BridgeHealth usage, non-goals.

### Phase 12 — Regulatory awareness docs

- `docs/REGULATORY.md` — IMDRF / IEC 62304 / FDA / EU MDR / AI-ML
  landscape, claims discipline, pre-pilot checklist. Non-binding.
- `docs/SAFETY_CASE.md` — GSN-style safety argument linking each
  claim to specific tests / modules.
- `docs/RISK_REGISTER.md` — ISO 14971-style hazard register across
  nine categories with pre- and post-mitigation scoring.
- `docs/ROADMAP.md` — Phase 12 entry added.

### Phase 9e — Speculative trio

- `integrations/marker_codec.py` — HMAC-signed QR-safe marker codec
  for denied-comms, casualty-bound handoff. Pure stdlib. Rejects
  tampered payloads, wrong secrets, and stale markers.
- `triage_reasoning/celegans_net.py` — `CelegansTriageNet`,
  fixed-topology 4/6/3 network with 45 hand-authored weights + motor
  biases. Auditable second-opinion classifier, no training loop.
- `mission_coordination/mission_triage.py` — fractal mission-as-
  casualty. `MissionSignature` (5 channels) → escalate / sustain /
  wind_down with contributions and reasons.
- `examples/marker_handoff_demo.py` — end-to-end encode → QR → decode
  + failure-mode rejection demo.
- `tests/test_phase9e.py` — 28 tests across all three modules plus a
  cross-module smoke.

### Phase 9d — Consolidation round 2

- `examples/full_pipeline_benchmark.py` extended with Bayesian twin
  posteriors, Eulerian stand-off HR, counterfactual replay, grounded
  explanations. New `--json` flag for CI-diffable output.
- `examples/bayesian_twin_demo.py`, `examples/crdt_sync_demo.py`,
  `examples/counterfactual_replay.py` — focused Phase 9 demo scripts.
- `docs/API.md` refreshed with every Phase 9 public symbol.
- `docs/ONE_PAGER.md` extended with Eulerian / Bayesian / CRDT / LLM
  grounding differentiators and a counterfactual line in the scorecard.
- New `docs/PHASE_9_SUMMARY.md` — one-page summary of all Phase 9 work.

### Phase 9c — Innovation pack, part 2

- `triage_reasoning/bayesian_twin.py` — particle filter over
  (priority_band, deterioration_rate) per casualty, returns a full
  posterior with ESS sanity flag.
- `evaluation/counterfactual.py` — retrospective what-if scorer with
  per-casualty regret.
- `triage_temporal/entropy_handoff.py` — Shannon-entropy-based handoff
  recommendation.
- `state_graph/crdt_graph.py` — OR-set + LWW-register + G-counter
  for denied-comms medic coordination.
- `signatures/acoustic_signature.py` — cough / wheeze / groan / silence
  bandpower detector.
- `triage_reasoning/llm_grounding.py` — grounded prompt builder plus
  `TemplateGroundingBackend` (LLM-free default).

### Phase 9b — Real-data classical calibration

- `triage_reasoning/score_fusion.py` — `MortalThresholds` override,
  closes the Larrey-gap from 9a.
- `perception/yolo_detector.py` — `LoopbackYOLODetector` plus
  `build_ultralytics_detector` lazy factory.
- `sim/realistic_dataset.py` — 70-case labelled dataset with edge
  cases and sensor-degradation noise.
- `triage_reasoning/calibration.py` — grid-search calibrator minimising
  critical_miss_rate first, macro_f1 second.
- `integrations/physionet_adapter.py` — `PhysioNetRecord` with
  `load_dict` (in-memory) and `load_wfdb` (lazy WFDB).
- `docs/ONE_PAGER.md` — grant-ready project summary.

### Phase 9a — Innovation pack, part 1

- `signatures/remote_vitals.py` — Eulerian-style bandpass extractor for
  stand-off vitals from ordinary RGB.
- `autonomy/active_sensing.py` — information-gain next-target planner.
- `triage_reasoning/larrey_baseline.py` — 1797 Larrey mortal /
  serious / light baseline classifier.

### Consolidation

- `tests/test_end_to_end.py` — two integration tests covering the full
  pipeline (perception → signatures → triage → graph → autonomy →
  bridge → evaluation).
- `examples/full_pipeline_benchmark.py` — runnable synthetic 8-casualty
  benchmark that prints a formatted Gate 1–4 + HMT scorecard.
- `.github/workflows/ci.yml` — GitHub Actions: Python 3.11/3.12 matrix,
  ruff + mypy + pytest + smoke run of the benchmark script.

### Phase 8 — platform integration

- `integrations/platform_bridge.py` — unified `PlatformBridge` Protocol
  plus `PlatformTelemetry` and `BridgeUnavailable`.
- `integrations/websocket_bridge.py` — `LoopbackWebSocketBridge`
  (in-memory deque) + FastAPI skeleton.
- `integrations/mavlink_bridge.py` — `LoopbackMAVLinkBridge` UAV
  simulator + `build_pymavlink_bridge` skeleton.
- `integrations/ros2_bridge.py` — `LoopbackROS2Bridge` with
  `published_on(kind)` / `inject_telemetry(...)` helpers +
  `build_rclpy_bridge` skeleton.
- `integrations/spot_bridge.py` — `LoopbackSpotBridge` with
  sit / stand / walk / trot gaits + `build_bosdyn_bridge` skeleton.

### Phase 7 — multimodal & DARPA gate evaluators

Part A:

- `signatures/thermal_signature.py` — hotspot / gradient / asymmetry.
- `signatures/posture_signature.py` — asymmetry / collapse / instability.
- `sim/sensor_degradation.py` — deterministic `SensorDegradationSimulator`.
- `triage_reasoning/uncertainty.py` — quality-weighted confidence
  propagation.
- `triage_reasoning/vitals_estimation.py` — FFT HR / RR estimator
  (Gate 4 foundation).

Part B (`triage4.evaluation/` subpackage):

- `gate1_find_locate.py` — greedy nearest-first matching,
  precision / recall / F1, localisation error.
- `gate2_rapid_triage.py` — priority classification accuracy, macro F1,
  confusion matrix, `critical_miss_rate`.
- `gate3_trauma.py` — multi-label per-kind metrics, micro / macro F1,
  mean Hamming accuracy.
- `gate4_vitals.py` — HR / RR MAE, RMSE, tolerance hit rate, MAPE.
- `hmt_lane.py` — human-machine teaming metrics (handoff timing,
  agreement, override, immediate timeliness).

### Phase 6.5 — upstream integration (10 rounds, 31 ports)

Shape / signature math adapted from `svend4/meta2`:

- `signatures/fractal/box_counting.py`
- `signatures/fractal/divider.py` (Richardson)
- `signatures/fractal/css.py` (Curvature Scale Space)
- `signatures/fractal/chain_code.py` (Freeman)
- `signatures/fractal_motion.py` — facade
- `matching/geometric_match.py` (pure-numpy replacement for cv2 path)
- `matching/curve_descriptor.py` (Fourier descriptor)

Matching / ranking / scoring:

- `matching/dtw.py`
- `matching/rotation_dtw.py`
- `matching/boundary_matcher.py` (Hausdorff / Chamfer / Fréchet)
- `matching/shape_match.py` — triage-facing wrapper
- `matching/affine_matcher.py` — pure-numpy RANSAC
- `matching/score_combiner.py` (`ScoreVector` / `CombinedScore`)
- `matching/score_normalizer.py` — minmax / zscore / rank
- `matching/candidate_ranker.py`
- `matching/pair_scorer.py`
- `matching/matcher_registry.py`
- `matching/orient_matcher.py`
- `scoring/threshold_selector.py` (Otsu / F-β / percentile / adaptive)
- `scoring/rank_fusion.py` (RRF / Borda)
- `scoring/evidence_aggregator.py`
- `scoring/pair_ranker.py`
- `scoring/pair_filter.py`
- `scoring/consistency_checker.py`
- `scoring/match_evaluator.py` (precision / recall / F-β)
- `scoring/global_ranker.py`

Radar signatures adapted from `svend4/infom`:

- `signatures/radar/heptagram.py` (7-axis)
- `signatures/radar/octagram.py` (8-axis + 3D compass)
- `signatures/radar/hexsig.py` (Q6 hypercube)

UI / protocol ports from `svend4/in4n`:

- `autonomy/route_planner.py` — BFS pathfinding
- `web_ui/src/components/SemanticZoom.tsx`
- `web_ui/src/components/InfoPanel.tsx`

Triage-native wrappers around upstream machinery:

- `state_graph/evidence_memory.py` — infom-style event log.
- `state_graph/graph_consistency.py` — uses upstream
  `ConsistencyReport` for triage-specific checks.
- `ui/html_export.py` — infom-pattern self-contained HTML.
- `integrations/meta2_adapter.py`, `infom_adapter.py`, `in4n_adapter.py`.

### Phase 6 — K3 fractal matrix (partial diagonal)

- `semantic/evidence_tokens.py` — K3-2.1 Evidence Semantics.
- `state_graph/body_state_graph.py` — K3-2.2 Relational Body-State.
- `triage_temporal/temporal_memory.py`,
  `triage_temporal/deterioration_model.py` — K3-2.3.
- `tactical_scene/map_projection.py` — K3-3.1.
- `mission_coordination/task_queue.py`,
  `mission_coordination/assignment_engine.py` — K3-3.2.
- `world_replay/timeline_store.py`,
  `world_replay/replay_engine.py` — K3-3.3.

### Phase 5 — autonomy & mission logic

- `autonomy/revisit.py`, `autonomy/human_handoff.py`,
  `autonomy/task_allocator.py`.

### Phase 4 — graph + dashboard MVP

- `graph/casualty_graph.py`, `graph/mission_graph.py`,
  `graph/updates.py`.
- `ui/dashboard_api.py` + `ui/seed.py`.
- `web_ui/` scaffolded with Map / Replay / CasualtyDetail pages.

### Phase 3 — signatures + triage MVP

- `signatures/breathing_signature.py`, `signatures/bleeding_signature.py`,
  `signatures/perfusion_signature.py`, `signatures/registry.py`.
- `triage_reasoning/rapid_triage.py`,
  `triage_reasoning/trauma_assessment.py`,
  `triage_reasoning/explainability.py`,
  `triage_reasoning/score_fusion.py`.

### Phase 2 — simulation-first perception

- `sim/casualty_profiles.py`, `sim/synthetic_benchmark.py`.
- `perception/body_regions.py`, `perception/person_detector.py` (stub),
  `perception/pose_estimator.py` (stub).

### Phase 1 — scaffold + core

- `core/models.py`, `core/enums.py`.
- `pyproject.toml`, `configs/sim.yaml`, `.gitignore`.
- Initial `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`,
  `docs/ANALYSIS.md`, `docs/darpa_mapping.md`.
- `third_party/ATTRIBUTION.md`, `LICENSES/`.

---

## Metrics

| After commit | Modules | Tests | Integration | CI |
|---|---|---|---|---|
| `efb7114` (Phase 1 scaffold) | 35 | 20 | — | — |
| `5f919f6` (Phase 6.5 complete) | 88 | 290 | — | — |
| `c9a188d` (Phase 7 complete) | 99 | 357 | — | — |
| `ee66ca4` (Phase 8 complete) | 104 | 378 | — | — |
| `3611d4d` (consolidation) | 104 | 380 | 2 end-to-end | GitHub Actions |

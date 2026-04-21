# Changelog

All notable changes to **triage4** are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com).

Work has been organised by numbered Phases of the roadmap; each Phase
is implemented by one or several commits on the feature branch.

---

## Unreleased / 0.1.0 — branch `claude/analyze-documents-structure-Ik1KX`

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

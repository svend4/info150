# triage4 — Roadmap

План развития проекта. Фазы выстроены так, чтобы каждая давала рабочий
результат и не блокировалась следующей.

## Phase 1 — Scaffold + core models (done)

- `pyproject.toml`, `.gitignore`, `configs/sim.yaml`
- `core/enums.py`, `core/models.py`
- базовые unit-тесты

## Phase 2 — Simulation-first perception MVP (done)

- `sim/casualty_profiles.py`
- `sim/synthetic_benchmark.py`
- `perception/body_regions.py`
- `perception/person_detector.py` (stub)
- `perception/pose_estimator.py` (stub)

## Phase 3 — Signatures + triage MVP (done)

- `signatures/breathing_signature.py`
- `signatures/bleeding_signature.py`
- `signatures/perfusion_signature.py`
- `signatures/fractal_motion.py`
- `signatures/registry.py`
- `triage_reasoning/rapid_triage.py`
- `triage_reasoning/trauma_assessment.py`
- `triage_reasoning/explainability.py`

## Phase 4 — Graph + dashboard MVP (done)

- `graph/casualty_graph.py`
- `graph/mission_graph.py`
- `graph/updates.py`
- `autonomy/human_handoff.py`
- `ui/dashboard_api.py`
- `web_ui/`

## Phase 5 — Autonomy + mission logic (done)

- `autonomy/revisit.py`
- `autonomy/task_allocator.py`
- `mission_coordination/task_queue.py`
- `mission_coordination/assignment_engine.py`

## Phase 6 — K3 extensions (partly done)

- [x] `semantic/evidence_tokens.py`
- [x] `state_graph/body_state_graph.py`
- [x] `triage_temporal/temporal_memory.py`
- [x] `triage_temporal/deterioration_model.py`
- [x] `tactical_scene/map_projection.py`
- [x] `world_replay/timeline_store.py`
- [x] `world_replay/replay_engine.py`
- [ ] 1.3 dynamic skeletal graph
- [ ] 2.2 conflict_resolver
- [ ] 3.3 forecast_layer

## Phase 6.5 — Upstream integration (complete)

Systematic mining of `svend4/meta2`, `svend4/infom`, `svend4/in4n` yielded
~25 directly reusable modules. Ten integration rounds covered:

- **Shape / signature math:** box_counting, divider (Richardson), CSS, chain
  code, curve_descriptor (Fourier), Hu-moments geometric_match.
- **Matching:** DTW, rotation_dtw, boundary_matcher (Hausdorff/Chamfer/
  Fréchet), affine_matcher (pure-numpy RANSAC), orient_matcher.
- **Scoring:** score_combiner, score_normalizer, threshold_selector,
  evidence_aggregator, rank_fusion (RRF/Borda), pair_ranker, pair_filter,
  match_evaluator (precision/recall/F-β), global_ranker,
  consistency_checker.
- **Infra:** candidate_ranker, matcher_registry.
- **Radar signatures:** heptagram, octagram, hexsig (Q6 hypercube).
- **Graph pattern:** evidence_memory (infom-inspired event log).
- **UI:** in4n_adapter force-graph export, SemanticZoom / InfoPanel React
  components, BFS route_planner, html_export.
- **Triage wrappers:** graph_consistency over upstream machinery.

Remaining upstream modules (~20 items: patch_matcher, feature_match,
text_flow, seam_score, `meta2/verification/*`, `meta2/algorithms/tangram/`
(cv2), etc.) are document-specific or cv2-heavy and deliver diminishing
returns for a triage project. Further upstream mining is officially closed
here; subsequent work shifts to Phase 7 (multimodal & field) and Phase 8
(platform integration).

## Phase 7 — Multimodal & field-hardening

- `signatures/thermal_signature.py`
- `signatures/posture_signature.py`
- `sim/sensor_degradation.py`
- `triage_reasoning/uncertainty.py`
- `triage_reasoning/vitals_estimation.py`
- `evaluation/gate1_find_locate.py`
- `evaluation/gate2_rapid_triage.py`
- `evaluation/gate3_trauma.py`
- `evaluation/gate4_vitals.py`
- `evaluation/hmt_lane.py`

## Phase 8 — Platform integration

- `integrations/ros2_bridge.py`
- `integrations/mavlink_bridge.py`
- `integrations/spot_bridge.py`
- `integrations/websocket_bridge.py`

## Риск-регистр

- **overexpansion** — не выходить за MVP без exit-criteria каждой фазы;
- **weak explainability** — каждый triage-вывод обязан иметь reasons;
- **platform lock-in** — держать сенсорные интерфейсы абстрактными;
- **medical overclaim** — decision-support framing, явный disclaimer в UI.

## Definition of success

`triage4` готов, когда может: принимать symuлированный поток → отслеживать
пострадавших → извлекать сигнатуры → давать triage priority с объяснениями →
хранить mission state как граф → показывать картину в tactical UI → упаковать
handoff для медика.

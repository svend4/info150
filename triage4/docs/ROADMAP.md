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

Signatures and reasoning (done):
- [x] `signatures/thermal_signature.py` — hotspot / gradient descriptor
- [x] `signatures/posture_signature.py` — asymmetry / collapse / instability
- [x] `sim/sensor_degradation.py` — deterministic noisy-input simulation
- [x] `triage_reasoning/uncertainty.py` — quality-weighted confidence
- [x] `triage_reasoning/vitals_estimation.py` — FFT HR / RR estimator

DARPA gate evaluations (done):
- [x] `evaluation/gate1_find_locate.py` — greedy nearest-first match,
      precision / recall / F1, localisation error
- [x] `evaluation/gate2_rapid_triage.py` — classification accuracy,
      macro F1, critical-miss rate
- [x] `evaluation/gate3_trauma.py` — multi-label P/R/F1 and Hamming
      accuracy across trauma kinds
- [x] `evaluation/gate4_vitals.py` — HR / RR MAE, RMSE, tolerance hit
      rate, MAPE
- [x] `evaluation/hmt_lane.py` — mean / max handoff time, agreement
      and override rates, immediate-timeliness rate

**Phase 7 complete.**

## Phase 8 — Platform integration

Unified contract (`integrations/platform_bridge.py`) and four loopback
platform bridges. Every bridge implements the `PlatformBridge` Protocol
and works in-process without any external SDK, so pipelines remain
testable by default. A real-backend skeleton is provided for each,
behind a lazy import that raises `BridgeUnavailable` with install
instructions.

- [x] `integrations/platform_bridge.py` — unified Protocol +
      `PlatformTelemetry`.
- [x] `integrations/websocket_bridge.py` — loopback + FastAPI skeleton.
- [x] `integrations/mavlink_bridge.py` — loopback UAV simulator +
      `pymavlink` skeleton.
- [x] `integrations/ros2_bridge.py` — loopback topic recorder +
      `rclpy` skeleton.
- [x] `integrations/spot_bridge.py` — loopback quadruped simulator +
      `bosdyn` skeleton.

**Phase 8 complete.**

## Phase 9a — Innovation pack, part 1

Three genuinely novel modules not ported from any upstream, grounded in
cross-domain ideas (MIT video magnification, Bayesian experimental
design, Napoleonic-era military medicine) and adapted to triage4's
existing contracts.

- [x] `signatures/remote_vitals.py` — Eulerian-style bandpass extractor
      for HR / RR signals from a plain RGB stack. Hands off to the
      existing ``VitalsEstimator``. Enables stand-off vitals from any
      camera, not just thermal or contact sensors.
- [x] `autonomy/active_sensing.py` — `ActiveSensingPlanner` ranks the
      next observation target by expected information gain
      (`uncertainty × priority_weight × novelty`). Plugs into the
      autonomy layer as a drop-in replacement for fixed coverage plans.
- [x] `triage_reasoning/larrey_baseline.py` — 1797-style mortal /
      serious / light classifier as an auditable baseline. Running it
      alongside `RapidTriageEngine` through Gate 2 immediately
      surfaced a calibration gap where the modern engine misses
      isolated heavy bleeding — now captured as a regression test in
      `tests/test_larrey_baseline.py`.

**Phase 9a complete.**

## Phase 9b — Real-data classical calibration

Prepared triage4 to meet real datasets and hardware without any runtime
breaking changes. The critical calibration gap from Phase 9a is closed.

- [x] `triage_reasoning/score_fusion.py` — `MortalThresholds` +
      override in `priority_from_score`. A single channel above its
      clinical threshold forces ``immediate`` regardless of the fused
      score. Closes the Larrey-gap identified in Phase 9a.
- [x] `perception/yolo_detector.py` — `LoopbackYOLODetector` (canned,
      deterministic) plus `build_ultralytics_detector` lazy factory.
      Replaces the `PersonDetector` stub without forcing every
      install to pull in PyTorch.
- [x] `sim/realistic_dataset.py` — 7 scenarios × N per-scenario
      labelled cases (default N=10 → 70 examples) with edge cases:
      isolated mortal signs, ambiguous mid-band, and sensor-degraded
      variants. The dataset every future calibration feeds on.
- [x] `triage_reasoning/calibration.py` — grid-search calibrator that
      optimises fusion weights + priority thresholds to minimise
      `critical_miss_rate` first and then maximise `macro_f1`.
- [x] `integrations/physionet_adapter.py` — `PhysioNetRecord` plus
      `load_dict` (in-memory, always works) and `load_wfdb` (lazy
      WFDB import). Integrates directly with `VitalsEstimator`.
- [x] `docs/ONE_PAGER.md` — grant-ready project summary with DARPA
      gate scorecard, differentiators, honest gaps, and ask.

**Phase 9b complete.**

## Phase 9c — Innovation pack, part 2

Six of the nine brainstorm ideas shipped as production-ready modules.
The remaining three ship as Phase 9e below.

- [x] `triage_reasoning/bayesian_twin.py` — `PatientTwinFilter`
      (particle filter, default 200 particles) over
      (priority_band, deterioration_rate). Upgrades the scalar
      `UncertaintyReport` to a full posterior distribution with
      effective-sample-size sanity.
- [x] `evaluation/counterfactual.py` — retrospective "what-if" scorer
      per casualty. Returns `CounterfactualCase` with regret score
      between actual and best-alternative priority.
- [x] `triage_temporal/entropy_handoff.py` — Shannon-entropy trigger
      that recommends medic handoff when the priority-observation
      stream plateaus. Avoids both premature and late handoffs.
- [x] `state_graph/crdt_graph.py` — `CRDTCasualtyGraph` with OR-set
      of ids, LWW-register per priority, G-counter per observation
      count. Merges are commutative + idempotent — denied-comms-ready.
- [x] `signatures/acoustic_signature.py` — cough / wheeze / groan /
      silence bandpower scorer. Fills the audio channel with a
      deterministic, non-ML baseline.
- [x] `triage_reasoning/llm_grounding.py` — prompt builder +
      `TemplateGroundingBackend` (LLM-free default). LLMs never make
      triage decisions — they only phrase the numeric facts triage4
      already decided. `LLMBackend` Protocol lets any provider
      (OpenAI, Anthropic, local) drop in without code changes.

**Phase 9c complete.**

## Phase 9e — Speculative trio (shipped)

The three ideas from the Phase 9 brainstorm that had been deferred as
"speculative" are now shipped as small, well-scoped modules. Each one
is independent, has no external deps, and is covered by focused tests:

- [x] `integrations/marker_codec.py` — steganographic battlefield
      markers. Encodes the essential triage fields of a `CasualtyNode`
      into an HMAC-signed JSON envelope (< 400 B, QR-safe). Pure
      stdlib, rejects tampered payloads, wrong secrets, and stale
      markers. Complements (does not replace) the CRDT path: CRDT is
      for medic-to-medic sync when tablets meet; markers are for a
      casualty-bound note that any responder can read offline.
- [x] `triage_reasoning/celegans_net.py` — `CelegansTriageNet`.
      Fixed-topology 4-sensory / 6-interneuron / 3-motor network with
      45 hand-authored, clinically-defensible weights. No training
      loop, no gradient, fully auditable. Complements the heuristic
      `RapidTriageEngine` as an independent second-opinion classifier.
- [x] `mission_coordination/mission_triage.py` — fractal
      mission-as-casualty. Treats the mission itself as a casualty
      with five signature channels (density, immediate fraction,
      unresolved sector fraction, medic utilisation, time-budget
      burn) and returns `escalate` / `sustain` / `wind_down`. Lets a
      commander see mission-level pressure with the same vocabulary
      as a patient.

Supporting work:
- [x] `examples/marker_handoff_demo.py` — end-to-end encode → QR →
      decode + tamper / wrong-secret / expired rejection demo.
- [x] `tests/test_phase9e.py` — 28 tests across the three modules
      plus a cross-module smoke (C.elegans classifies a signature →
      marker encodes the node → decoded priority matches).

**Phase 9e complete.**

## Phase 12 — Regulatory awareness

Pre-clinical documentation that anticipates the regulatory framework
*if* triage4 ever moves toward a medical product. Non-binding; not
legal advice. Written to surface known gaps so they can be closed
before any clinical pilot, not to claim compliance.

- [x] `docs/REGULATORY.md` — IMDRF SaMD classification (target
      Class III), IEC 62304 safety-class analysis (Class C),
      FDA De Novo / 510(k) pathway notes, EU MDR notes, AI/ML
      considerations (GMLP, PCCP), HIPAA / GDPR overlay, claims
      discipline, pre-pilot checklist.
- [x] `docs/SAFETY_CASE.md` — GSN-style top goal + four sub-goals
      (output correctness, failure-mode safety, operator-in-the-loop,
      data integrity) + assurance continuity, each backed by specific
      test / module evidence.
- [x] `docs/RISK_REGISTER.md` — ISO 14971-style register covering
      calibration, safety-critical classification, operator-in-the-
      loop, data integrity, platform bridges, cybersecurity, build /
      CI, claims / regulatory, and UI hazards. Each row scored
      pre- and post-mitigation, with gate flags on residuals ≥ 6.

**Phase 12 complete.** (Docs only — no code changes.)

## Риск-регистр (краткий)

См. `docs/RISK_REGISTER.md` для полного реестра. Краткая сводка
основных категорий:

- **overexpansion** — не выходить за MVP без exit-criteria каждой фазы;
- **weak explainability** — каждый triage-вывод обязан иметь reasons;
- **platform lock-in** — держать сенсорные интерфейсы абстрактными;
- **medical overclaim** — decision-support framing, явный disclaimer в UI.

## Definition of success

`triage4` готов, когда может: принимать symuлированный поток → отслеживать
пострадавших → извлекать сигнатуры → давать triage priority с объяснениями →
хранить mission state как граф → показывать картину в tactical UI → упаковать
handoff для медика.

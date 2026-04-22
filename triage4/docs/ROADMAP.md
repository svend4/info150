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
- [x] 1.3 dynamic skeletal graph — `state_graph/skeletal_graph.py`
- [x] 2.2 conflict_resolver — `state_graph/conflict_resolver.py`
- [x] 3.3 forecast_layer — `world_replay/forecast_layer.py`

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

## Phase 10-prep — Hardware integration scaffold

Preparatory work for Phase 10 proper (live UAV / quadruped / camera
integration). Phase 10 itself needs physical hardware and external
SDKs; this sub-phase ships the scaffold so that when hardware lands,
wiring is a 1-day task per platform rather than a from-scratch
investigation.

- [x] `triage4/integrations/bridge_health.py` — `BridgeHealth`
      dataclass + `check_bridge_health(bridge)` / `check_telemetry(tm)`
      / `safe_to_dispatch(health)`. Uniform failure-mode surface for
      any `PlatformBridge`: empty platform_id, disconnected,
      non-finite pose, out-of-range or low battery, stale telemetry,
      platform_id mismatch between bridge and snapshot.
- [x] Real-backend factory skeletons fleshed out in
      `ros2_bridge.build_rclpy_bridge`,
      `mavlink_bridge.build_pymavlink_bridge`,
      `spot_bridge.build_bosdyn_bridge`,
      `websocket_bridge.build_fastapi_websocket_bridge`. Each carries
      concrete SDK call outlines matching the current vendor APIs;
      still raises `NotImplementedError` to prevent silent shipping.
- [x] `tests/test_bridges_contract.py` — 29 Protocol-conformance +
      health-check tests. Every Loopback bridge satisfies
      `isinstance(bridge, PlatformBridge)`, roundtrips every publish
      method, and respects `close()`. Real-backend factories must
      raise `BridgeUnavailable` or `NotImplementedError`, never
      silently succeed.
- [x] `docs/HARDWARE_INTEGRATION.md` — per-platform wiring guide
      (ROS2 topics, MAVLink frame-swap note, bosdyn lease lifecycle,
      WebSocket security), BridgeHealth usage, first-flight
      checklist, optional-dep layout, non-goals, open questions.

**Phase 10-prep complete.** Phase 10 proper still needs real HW.

## Phase 13-prep — Deployment patterns

Preparatory work for Phase 13 proper (production deployment). No
customer is targeted yet; this sub-phase ships reference artefacts
and a test suite that locks the security-relevant flags so a future
deployment can ship in a day rather than a week.

- [x] `Dockerfile` — multi-stage `python:3.12-slim` build, runs as
      unprivileged `triage` user, includes a `HEALTHCHECK`, image
      size < 200 MB (no SDKs, only numpy + scipy + fastapi + triage4).
- [x] `.dockerignore` — keeps `tests/`, `docs/`, `web_ui/`, `.git/`,
      and caches out of the image.
- [x] `docker-compose.yml` — `read_only: true`, `cap_drop: ALL`,
      `no-new-privileges`, healthcheck, 127.0.0.1:8000 binding only,
      optional `edge` profile that adds an nginx reverse proxy.
- [x] `deploy/triage4.service` — systemd unit with
      `NoNewPrivileges`, `ProtectSystem=strict`,
      `MemoryDenyWriteExecute`, `SystemCallFilter=@system-service`,
      1 GB memory cap, runs as user `triage`.
- [x] `configs/production.yaml` — conservative thresholds, operator
      confirmation on every `immediate`, autonomous waypoint
      dispatch disabled by default, three security env-var slots
      (blank so unconfigured deployments fail loud).
- [x] `configs/edge.yaml` — denied-comms overlay: CRDT + marker
      codec enabled, tighter power warning, reduced retention.
- [x] `configs/nginx.conf` — reverse-proxy template with TLS 1.2+,
      security headers, rate-limit zone, commented-out bearer-token
      check.
- [x] `docs/DEPLOYMENT.md` — footprint numbers, three profiles
      (container / systemd / edge), config pattern, secret handling,
      networking, observability, upgrade / rollback, 10-item
      pre-deployment checklist, non-goals, open questions for
      Phase 13 proper.
- [x] `tests/test_deployment_artifacts.py` — 19 smoke tests that
      parse each deployment artefact and assert the security-
      relevant flags (unprivileged user, read-only FS, no blank
      secrets, TLS enforced).

**Phase 13-prep complete.** Phase 13 proper still needs a customer.

## Level A follow-ups — Closing documented gaps

Four discrete items that close explicitly-tracked gaps from
`RISK_REGISTER.md` and the open questions in the Phase 10-prep /
13-prep docs. All four are pure-Python, no new runtime deps, and
shipped together on this branch.

- [x] `scripts/claims_lint.py` + `tests/test_claims_lint.py` —
      scans user-facing `.md` + Python docstrings for framing
      claims ("diagnose", "FDA-cleared", "medical device",  [claims-lint: allow]
      "product can treat", ...). Allowlists `REGULATORY.md`,
      `RISK_REGISTER.md`, `SAFETY_CASE.md`. Supports inline
      `[claims-lint: allow]` markers. Wired into CI. Closes
      **CLAIM-001** gate.
- [x] `pyproject.toml [tool.mutmut]` + `scripts/run_mutation.sh`
      + `docs/MUTATION_TESTING.md` + `tests/test_mutation_config.py`
      — mutmut scoped to the 7 triage-critical modules. Opt-in
      (not CI-gated yet due to runtime). Closes **CI-002** gate.
- [x] `triage4/integrations/multi_platform.py` +
      `tests/test_multi_platform.py` — `MultiPlatformManager`
      orchestrator. Satisfies `PlatformBridge` protocol, supports
      broadcast + targeted publish, health-gated waypoint dispatch,
      auto-picks healthiest platform. Addresses HARDWARE_INTEGRATION
      §7 open question.
- [x] `triage4/ui/metrics.py` + `tests/test_metrics.py` —
      stdlib-only Prometheus text-format exposition. Three metric
      families: `triage4_casualties_total` (counter per priority),
      `triage4_handoff_latency_seconds` (histogram), and
      `triage4_bridge_health` (gauge per platform/state) plus
      uptime. Wired into `dashboard_api` as `GET /metrics`.
      Addresses DEPLOYMENT §9 open question.

**Level A complete.**

## Level B — Developer experience polish

- [x] `Makefile` — 24 targets, self-documenting `make help`. Covers
      install / QA / benchmark / demos / mutation / SBOM / Docker.
- [x] `CONTRIBUTING.md` — scope, workflow, test conventions, claims
      discipline, safety-critical change protocol, do-nots.
- [x] `README.md` — refreshed status table (Phases 1–9e + Level A),
      test count, `make` quickstart, expanded docs index.
- [x] `scripts/generate_sbom.py` + `tests/test_generate_sbom.py` —
      CycloneDX 1.5 SBOM generator with `cyclonedx-py` CLI path and
      stdlib fallback. Referenced by `make sbom` and the
      `DEPLOYMENT.md` pre-deploy checklist.
- [x] `tests/test_properties.py` — 9 hypothesis property-based
      tests. Proved CRDT merge is commutative / idempotent /
      associative across randomised event histories; verified
      marker encode/decode roundtrip, QR roundtrip, single-byte-
      flip rejection, wrong-secret rejection; score-fusion
      bleeding-monotonicity and unit-interval invariant.
- [x] `integrations/marker_codec.py` — hardened: malformed base64
      signature and out-of-range payload fields now raise
      `InvalidMarker` instead of letting the underlying exceptions
      escape. Bug surfaced by the property test.

**Level B complete.**

## Level C — Optional refinement (benchmarks + demos + docs)

- [x] `examples/stress_benchmark.py` — scaling + memory stress
      benchmark. Generates synthetic scenes of configurable size,
      times the triage hot path, reports per-casualty µs and KB,
      plus a slope estimate (linear / sub-linear / super-linear).
      At 5000 casualties: ~11 µs/casualty, ~280 bytes/casualty,
      linear scaling. Wired into `make stress` / `make stress-big`.
- [x] `examples/multi_platform_demo.py` — runnable demo of the
      `MultiPlatformManager` orchestrating UAV + Spot + ROS2
      bridges (broadcast, targeted publish, health gating,
      auto-pick, stale-telemetry refusal).
- [x] `examples/calibration_walkthrough.py` — end-to-end demo:
      70-case realistic dataset → baseline → grid-search calibrate
      → calibrated engine → side-by-side comparison table.
- [x] `examples/mission_replay_demo.py` — 6-tick mission with a
      mid-mission priority revision; replayed via `TimelineStore`
      + `ReplayEngine`, plus `frame_at(index)` random-access.
- [x] `docs/CALIBRATION.md` — what gets calibrated and what does
      not, dataset description, API walkthrough, when-to-
      recalibrate, real-data (PhysioNet) path.
- [x] `docs/EXPLAINABILITY.md` — three explanation layers (reasons
      list / per-channel confidence / NL summary), LLM-grounding
      Protocol, observability (`/explain` endpoint, logs,
      Prometheus), explicit non-goals (no SHAP / no saliency here).
- [x] `Makefile` extended with `demo-multi`, `demo-calibration`,
      `demo-replay`, `stress`, `stress-big` targets.
- [x] `.github/workflows/ci.yml` — Level C demos added to the
      smoke-run step so they can't silently rot.
- [x] `README.md` — docs index + quickstart lists the new demos.

**Level C complete.**

## K3 matrix closure — 3 remaining cells shipped

All 9 cells of the K3 matrix now have concrete implementations.
These three were the only technical work left that did not depend
on external resources.

- [x] **K3-1.3 Dynamic skeletal graph** —
      `state_graph/skeletal_graph.py`. 13-joint humanoid skeleton
      with time-stamped observations, per-joint wound intensity,
      motion score (path length per second, clipped to [0, 1]),
      wound slope (least-squares trend), and left-vs-right
      asymmetry reports across 5 mirror pairs. 26 tests.
- [x] **K3-2.2 Conflict resolver** —
      `state_graph/conflict_resolver.py`. `ConflictResolver` takes
      raw hypothesis scores + a support / conflict knowledge
      base, applies single-pass support boosts and conflict
      penalties, and groups mutually-exclusive hypotheses into
      conflict cliques with a declared winner per group. Ships
      with a default knowledge base covering hemorrhage / shock
      / respiratory / posture hypotheses. 17 tests.
- [x] **K3-3.3 Forecast layer** —
      `world_replay/forecast_layer.py`. `ForecastLayer` projects
      casualty urgency (blending linear extrapolation + the
      existing `DeteriorationModel` trend; returns a
      `CasualtyForecast` with priority band + confidence) and
      mission state (extrapolates the 5 channels of
      `MissionSignature`, feeds result back through
      `classify_mission`; returns a `MissionForecast`). 21 tests.

Combined: 64 new tests, 0 new runtime deps, pure stdlib math.



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

# triage4-sport — status

Honest accounting.

## Built

- Package scaffold.
- `docs/PHILOSOPHY.md` — three-audience posture +
  injury-prediction overreach + athlete-data-sensitivity.
- `triage4_sport.core`:
  - `enums`: `Sport` (soccer / basketball / tennis /
    baseball / sprint / swim), `RiskBand` (steady /
    monitor / hold), `ChannelKind` (form_asymmetry /
    workload_load / recovery_hr / baseline_deviation /
    calibration), `MovementKind` (sport-specific
    movement labels — kick / throw / serve / stride /
    jump).
  - `models`: `MovementSample`, `WorkloadSample`,
    `RecoveryHRSample`, `AthleteBaseline`,
    `AthleteObservation`, `PerformanceAssessment`,
    `CoachMessage` (strict guard), `TrainerNote`
    (intermediate guard), `PhysicianAlert` (permissive-
    clinical guard + reasoning_trace required),
    `SessionReport`.
- `triage4_sport.signatures`:
  - `form_asymmetry` — limb / movement-pattern
    asymmetry score.
  - `workload_load` — rapid-spike-vs-baseline workload
    detector (acute:chronic ratio inspired).
  - `recovery_hr` — post-session HR recovery rate.
  - `baseline_deviation` — multi-channel deviation
    from per-athlete baseline.
- `triage4_sport.sport_engine`:
  - `performance_bands` — sport-agnostic threshold bands.
  - `monitoring_engine.SportPerformanceEngine.review(
    observation, baseline)` → `SessionReport`.
- `triage4_sport.sim`:
  - `synthetic_session` — deterministic generator.
  - `demo_runner` — `make demo` entry point.
- `tests/` — model / signature / engine coverage.

## Not built

- **Sport-specific movement classifier.** Upstream (per-
  sport pose model). The library consumes already-
  classified movement features.
- **GPS-vest data ingestion** (Catapult / WIMU /
  StatSports). Upstream responsibility; library accepts
  already-derived `WorkloadSample` records.
- **Injury-risk temporal-CNN model.** Out of scope for
  this MVP — would require labelled historical injury
  data from a partner team.
- **Multi-week baseline learner.** Per-athlete baseline
  is consumer-app responsibility; the library accepts a
  pre-computed `AthleteBaseline` as engine input.
- **Coach / trainer / physician dashboards.** Library
  produces dataclass records; UIs live downstream.

## Scope boundary

- **No injury prediction.** The library NEVER says
  "predicts injury". It flags precursor patterns for
  human-trainer review.
- **No definitive diagnosis.** Even the PhysicianAlert
  refuses definitive language ("ACL tear", "fracture
  confirmed"). The team physician examines and decides.
- **No athlete-identity persistence.** Per-session
  opaque tokens only. Cross-session matching belongs in
  a separate consumer app with CBA / GDPR review.
- **No career-jeopardy framing.** "Will be cut", "will
  lose contract", "roster decision" all rejected at
  construction.

If a future version crosses any of these boundaries, fork
into a separate codebase with the appropriate league CBA
+ data-rights legal review.

# triage4-site — status

Honest accounting. Marketing language stays out of this file.

## Built

- Package scaffold (`pyproject.toml`, `Makefile`, `.gitignore`).
- `docs/PHILOSOPHY.md` — the five-boundary posture
  (clinical + operational + privacy + dignity + labor-
  relations) and the forbidden-vocabulary lists.
- `triage4_site.core`:
  - `enums`: `AlertLevel` (ok / watch / urgent), `AlertKind`
    (ppe / lifting / heat / fatigue / calibration),
    `PPEItem` (hard_hat / vest / harness / glasses),
    `SiteCondition` (clear / dusty / rainy / low_light).
  - `models`: `PPESample`, `LiftingSample`, `ThermalSample`,
    `FatigueGaitSample`, `WorkerObservation`, `SafetyScore`,
    `SafetyOfficerAlert` (with 5-boundary claims guard),
    `SiteReport`.
- `triage4_site.signatures`:
  - `ppe_compliance` — fraction of observation window where
    all required items were detected, aggregated to a
    compliance score in [0, 1].
  - `lifting_posture` — worst (most-unsafe) back-hip angle
    observed during a lift, mapped to a posture score.
  - `heat_stress` — ACGIH TLV-style skin-ambient differential
    combined with recent slowdown indicator.
  - `fatigue_gait` — pace trend across the shift + limb
    asymmetry, fused into a single wellness channel.
- `triage4_site.site_monitor`:
  - `safety_bands` — OSHA / NIOSH / ACGIH-sourced threshold
    defaults wrapped in a tunable dataclass.
  - `monitoring_engine.SiteSafetyEngine.review(site_id,
    observations, conditions=None)` → `SiteReport`.
- `triage4_site.sim`:
  - `synthetic_shift` — deterministic shift generator tunable
    across PPE gaps, unsafe lifts, heat-stress intensity,
    fatigue decline.
  - `demo_runner` — entry point for `make demo`.
- `tests/` — tests across models, signatures, and engine.

## Not built

- **Per-worker PPE detector.** YOLO-family PPE detection is
  the production upstream; this library consumes already-
  classified `PPESample` events.
- **RFID-badge integration.** Worker IDs are opaque tokens.
  The sensor hub is responsible for badge → token mapping.
- **Near-miss / struck-by detection.** The 3D tool-path vs.
  worker-trajectory logic is a separate class of signature
  and out of MVP scope.
- **Site-ops dashboard.** The library produces
  `SafetyOfficerAlert` records; the UI belongs in a consumer
  app with its own IA.
- **Alert-fatigue aggregation to hot zones.** The MVP emits
  per-observation alerts; a downstream layer rolls them up
  to "area X has N PPE-alerts this hour". Aggregation is
  noted as essential in the adaptation file — out of MVP
  scope for this library.
- **Retention policy enforcement.** Data-retention ≤ 30 days
  and "no cross-shift individual metrics" are product-layer
  commitments — the library provides the hooks (opaque IDs,
  no cross-shift state) but enforcement is an infrastructure
  layer.

## Scope boundary (repeated for emphasis)

- **Clinical:** never diagnoses heat stroke, musculoskeletal
  injury, dehydration, or any clinical condition.
- **Operational:** never stops work, shuts down the site,
  sends workers home, or triggers discipline. The safety
  officer decides.
- **Privacy:** opaque worker tokens only. No face
  recognition. No cross-shift identity.
- **Dignity:** alerts describe observations, not the worker
  ("unsafe lifting angle observed", not "careless worker").
- **Labor relations (NEW in this sibling):** no per-worker
  performance metrics. No "productivity" / "efficiency" /
  "write-up" / "discipline" vocabulary. Data surfaces are
  hot-zone + crew level, not individual-performance level.

Crossing any of the five lines is a separate product with a
separate regulatory framing. Don't erode them inside one
codebase.

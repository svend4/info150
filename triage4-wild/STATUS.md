# triage4-wild — status

Honest accounting.

## Built

- Package scaffold.
- `docs/PHILOSOPHY.md` — three new boundaries (field-
  security, poaching-prediction overreach, ecosystem-
  prediction overreach), SMS-length rationale.
- `triage4_wild.core`:
  - `enums`: `Species` (elephant / rhino / lion / buffalo
    / giraffe / zebra / cheetah / unknown), `AlertLevel`
    (ok / watch / urgent), `AlertKind` (gait / thermal /
    collapse / body_condition / calibration),
    `ThreatKind` (snare_injury / thermal_asymmetry /
    gait_instability / body_condition_low / collapse),
    `CaptureQuality` (good / partial / night_ir).
  - `models`: `LocationHandle` (opaque grid-cell token,
    never plaintext coordinates), `QuadrupedPoseSample`,
    `ThermalSample`, `GaitSample`, `BodyConditionSample`,
    `WildlifeObservation`, `WildlifeHealthScore`,
    `RangerAlert` (SMS-length cap + field-security guard
    + poaching-overreach guard + ecosystem-overreach
    guard + standard clinical/operational guards),
    `ReserveReport`.
- `triage4_wild.signatures`:
  - `quadruped_gait` — limb asymmetry across paired
    fore / hind joints. Species-agnostic at signature
    level.
  - `thermal_asymmetry` — wound/inflammation heat
    signature.
  - `postural_collapse` — down-and-not-rising vs.
    ordinary rest pattern.
  - `body_condition` — emaciation score from
    frame-geometry proxy.
- `triage4_wild.wildlife_health`:
  - `species_thresholds` — per-species alert thresholds
    + species-specific red-flag adjustments (elephant
    tusk asymmetry; rhino horn cracks — placeholder for
    the upstream red-flag classifier output).
  - `monitoring_engine.WildlifeHealthEngine.review(
    observation)` → `ReserveReport`.
- `triage4_wild.sim`:
  - `synthetic_reserve` — deterministic
    camera-trap-pass generator.
  - `demo_runner` — `make demo` entry point.
- `tests/` — model / signature / engine coverage.

## Not built

- **Species classifier.** Upstream (MegaDetector,
  iNaturalist, Snapshot-Serengeti YOLO weights). The
  library consumes species + confidence fields on the
  observation.
- **GPS-collar telemetry adapter.** Upstream
  responsibility (Iridium / LoRa). Plaintext coordinates
  never enter the library.
- **Red-flag visual classifier (wire-snare, tusk, horn).**
  Upstream responsibility; the library consumes a
  confidence score.
- **Ranger-handoff delivery (satcom / SMS).** The library
  produces `RangerAlert` records; the satcom bridge lives
  downstream.
- **Reserve calibration.** Thresholds are literature
  placeholders; real deployments tune per-reserve with
  partnership data.

## Scope boundary

- **No clinical diagnosis.** Wildlife vet acts are out
  of scope.
- **No patrol recommendation.** The library never
  proposes where rangers should go, only which
  observation needs ranger + reserve-vet review.
- **No plaintext location.** Field-security boundary
  is load-bearing. Enforced architecturally via
  `LocationHandle` + claims guard on `RangerAlert`.
- **No ecosystem prediction.** The library describes
  an observation pass, not an outcome trajectory.

If a future version produces actual patrol guidance,
ingests human-presence data, or predicts poaching
events, fork separately with its own ethics-review
framework.

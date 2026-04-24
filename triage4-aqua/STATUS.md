# triage4-aqua — status

Honest accounting. Marketing stays out.

## Built

- Package scaffold (`pyproject.toml`, `Makefile`, `.gitignore`).
- `docs/PHILOSOPHY.md` — seven-boundary posture (clinical,
  operational, privacy, dignity, labor-relations, panic-
  prevention, no-false-reassurance) + lifeguard-replacement-
  prevention posture.
- `triage4_aqua.core`:
  - `enums`: `AlertLevel` (ok / watch / urgent),
    `AlertKind` (submersion / idr / absent / distress /
    calibration), `PoolCondition` (clear / turbid /
    sun_glare / crowded), `WaterZone` (pool / beach /
    wave_pool / lazy_river / lap_lanes).
  - `models`: `SurfacePoseSample`, `SubmersionSample`,
    `SwimmerPresenceSample`, `SwimmerObservation`,
    `AquaticScore`, `LifeguardAlert` (7-boundary claims
    guard), `PoolReport`.
- `triage4_aqua.signatures`:
  - `submersion_duration` — longest consecutive below-
    surface run, mapped against the 4-6 min drowning
    window.
  - `idr_posture` — vertical-body + head-low + non-rhythmic
    pattern classifier (Wiki 2010, Pia 2006).
  - `absent_swimmer` — time since last `presence=active`
    sample exceeds threshold.
  - `surface_distress` — pre-submersion IDR visible above
    water.
- `triage4_aqua.pool_watch`:
  - `drowning_bands` — submersion + IDR thresholds, tunable.
  - `monitoring_engine.PoolWatchEngine.review(pool_id,
    observations)` → `PoolReport`.
- `triage4_aqua.sim`:
  - `synthetic_pool` — deterministic swimmer-observation
    generator.
  - `demo_runner` — `make demo` entry point.
- `tests/` — model / signature / engine coverage.

## Not built

- **Underwater swimmer detection.** Entire perception
  pipeline lives upstream; this library consumes
  already-classified surface + submersion events.
- **IDR visual classifier.** Upstream responsibility.
- **Person re-identification across cameras.** The
  library accepts pre-tracked swimmer_tokens and never
  attempts re-identification.
- **Lifeguard-pendant integration.** The library
  produces `LifeguardAlert` records; the pendant /
  smartwatch delivery lives downstream.
- **EMS escalation flow.** Alerts surface to lifeguards,
  never directly to EMS / 911.
- **Video storage or re-playback UI.** Out of scope;
  privacy posture.
- **Per-pool calibration.** Submersion thresholds + IDR
  confidence cut-offs are from the published drowning-
  response literature; real deployments tune per-pool
  with instructor-labelled events.

## Scope boundary (repeated for emphasis)

- **Clinical:** never diagnoses cardiac arrest, secondary
  drowning, or any medical event.
- **Operational:** lifeguard-pendant / smartwatch alerting
  is the output. EMS escalation stays with the lifeguard.
- **Privacy:** anonymous swimmer tokens only; no video
  storage; no age / appearance / swimsuit descriptions;
  particularly strict for minors.
- **Dignity:** describes observations ("swimmer in zone
  X, submersion 42 s"), never "drowning victim".
- **Labor-relations:** no lifeguard performance metrics
  derived from the signals; no "lifeguard missed this".
- **Panic-prevention:** the library is urgent when it
  needs to be, but it never characterises events with
  dramatic framing ("tragedy unfolding", "lethal").
- **No-false-reassurance (NEW in this sibling):** never
  asserts safety. A window with no drowning signatures
  is described as "no drowning signature in this
  cycle", never "pool is safe".

If a future version produces EMS-dispatch commands or
video-upload records, that work belongs in a separate
regulated codebase with jurisdiction-specific review.

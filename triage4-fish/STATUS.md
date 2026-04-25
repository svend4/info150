# triage4-fish — status

Honest accounting.

## Built

- Package scaffold.
- `docs/PHILOSOPHY.md` — multi-modal fusion +
  antibiotic-dosing-overreach + failure-cost-asymmetry
  posture.
- `triage4_fish.core`:
  - `enums`: `Species` (salmon / trout / sea_bass /
    tilapia / unknown), `WelfareLevel` (steady / watch /
    urgent), `AlertKind` (gill_rate / school_cohesion /
    sea_lice / mortality_floor / water_chemistry /
    calibration), `WaterCondition` (clear / turbid /
    silt_storm), `OutbreakIndicator`.
  - `models`: `GillRateSample`, `SchoolCohesionSample`,
    `SeaLiceSample`, `MortalityFloorSample`,
    `WaterChemistrySample`, `PenObservation`,
    `PenWelfareScore`, `FarmManagerAlert` (multi-list
    guard with antibiotic-dosing-overreach as the
    new boundary), `PenReport`.
- `triage4_fish.signatures`:
  - `gill_rate` — pen-aggregate gill rate vs species
    band.
  - `school_cohesion` — schooling-behaviour metric.
  - `sea_lice_burden` — confidence-weighted lice count
    proxy.
  - `mortality_floor` — dead-fish accumulation rate.
  - `water_chemistry` — DO / temperature / salinity /
    turbidity vs species reference range.
- `triage4_fish.pen_health`:
  - `species_aquatic_bands` — per-species RR + water
    range references.
  - `monitoring_engine.AquacultureHealthEngine.review(
    observation, farm_id)` → `PenReport`. CROSS-MODAL
    weighting: poor water chemistry scales down the
    visible-light channel weights (turbid water + low
    DO → less confident vision read), and vision-channel
    deviations co-occurring with poor water chemistry
    receive a corroboration note in the alert.
- `triage4_fish.sim`:
  - `synthetic_pen` — deterministic generator with
    multi-modal samples.
  - `demo_runner` — `make demo` entry point.
- `tests/` — model / signature / engine coverage.

## Not built

- **Underwater image preprocessing.** Visibility < 5 m,
  particle occlusion, blue-shift colour correction —
  upstream responsibility (Fishial.ai / LSSS pipeline).
  The library consumes already-extracted samples.
- **Sea-lice visual classifier.** Upstream (commercial
  trained models exist — Umitron, ObservFood). The
  library accepts confidence + count proxy.
- **Fish skeletal topology.** Out of MVP scope. The
  library uses pen-aggregate samples, not per-fish
  pose.
- **Water-chemistry sensor integration.** Upstream
  responsibility — bundled pen sensors (DO probe,
  temperature, salinity, turbidity meters) push
  `WaterChemistrySample` records.
- **Mortality-floor visual classifier.** Upstream.
- **Welfare-report KPI UI / commercial-yield
  dashboard.** Library produces `FarmManagerAlert`
  records; UI lives downstream.
- **Per-pen calibration.** Thresholds are EU Directive
  98/58/EC + aquaculture-literature placeholders.

## Scope boundary

- **No antibiotic-dosing recommendations.** Antibiotic
  / antimicrobial dosing is veterinary practice. The
  library NEVER says "administer X mg/kg" — it says
  "consult veterinarian" and surfaces observation
  patterns.
- **No outbreak diagnosis.** The library flags
  candidate disease patterns; a vet + sampling lab
  diagnose.
- **No per-fish identity.** Pen-level aggregate by
  design.
- **No commercial-yield calculation.** Welfare
  observations only.
- **No false reassurance.** Absence of alerts is NOT a
  clearance — see the failure-cost-asymmetry posture
  in docs/PHILOSOPHY.md.

If a future version produces dosing recommendations,
that work crosses into veterinary therapeutics + EU
Directive 2019/6 (veterinary medicinal products) and
needs a separate regulated codebase.

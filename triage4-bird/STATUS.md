# triage4-bird — status

Honest accounting.

## Built

- Package scaffold.
- `docs/PHILOSOPHY.md` — surveillance-overreach + audio-
  privacy + acoustic-first posture.
- `triage4_bird.core`:
  - `enums`: `Species` (mallard / robin / sparrow /
    raven / hawk / finch / swift / unknown), `AlertLevel`
    (ok / watch / urgent), `AlertKind` (call_presence /
    distress / vitals / thermal / mortality_cluster /
    calibration), `CallKind` (song / chip / alarm /
    distress).
  - `models`: `CallSample` (already-classified — never
    raw audio), `WingbeatSample`, `BodyThermalSample`,
    `DeadBirdCandidate`, `BirdObservation`,
    `AvianHealthScore`, `OrnithologistAlert` (multi-
    boundary guard), `StationReport`.
- `triage4_bird.signatures`:
  - `call_presence` — species-mix vs. expected profile.
  - `distress_rate` — fraction of calls flagged distress.
  - `wingbeat_vitals` — wing-beat frequency check.
  - `febrile_thermal` — body-temp anomaly proxy.
  - `mortality_cluster` — count of dead-bird candidates.
- `triage4_bird.bird_health`:
  - `species_acoustic_bands` — per-species call-rate
    + wingbeat-frequency reference bands.
  - `monitoring_engine.AvianHealthEngine.review(observation,
    station_id)` → `StationReport`.
- `triage4_bird.sim`:
  - `synthetic_station` — deterministic generator.
  - `demo_runner` — `make demo` entry point.
- `tests/` — model / signature / engine coverage.

## Not built

- **Raw-audio processing**. Library never accepts
  waveforms. Upstream BirdNET (or equivalent) does
  call classification + voice-content discard.
- **Visual species classifier**. Upstream responsibility.
- **Ringing / banding cross-reference**. Out of MVP
  scope.
- **Multi-station migration aggregation**. Out of MVP
  scope.
- **Avian-flu surveillance lab integration**. The
  library produces `OrnithologistAlert` records for
  candidate mortality clusters; downstream sampling
  workflow integration lives elsewhere.

## Scope boundary

- **No clinical diagnosis** of avian flu / HPAI / any
  disease. The library flags candidate mortality
  patterns; sampling labs make the diagnosis call.
- **No raw audio**. Library refuses waveform inputs;
  voice-content discard is upstream.
- **No multi-station aggregation**. Per-station
  observation only.
- **No plaintext coordinates**. Field-security boundary
  inherited from triage4-wild.

If a future version diagnoses HPAI, the library has
crossed into clinical / public-health territory and
needs a separate regulated codebase with USDA APHIS /
EFSA review.

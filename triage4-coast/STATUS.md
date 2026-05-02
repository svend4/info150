# triage4-coast — status

Honest accounting. Marketing stays out.

## Built

- Package scaffold (`pyproject.toml`, `Makefile`, `.gitignore`).
- `docs/PHILOSOPHY.md` — six-boundary posture (clinical,
  operational, privacy, dignity, labor-relations, panic-
  prevention) + neutrality posture.
- `triage4_coast.core`:
  - `enums`: `AlertLevel`, `AlertKind` (density / flow /
    pressure / medical / calibration), `ZoneKind`
    (seating / standing / egress / transit_platform /
    concourse), `CrowdDirection` (static / in / out /
    crossflow / mixed).
  - `models`: `DensityReading`, `FlowSample`,
    `PressureReading`, `MedicalCandidate`,
    `ZoneObservation`, `CrowdScore`, `VenueOpsAlert` (with
    six-boundary claims guard), `VenueReport`.
- `triage4_coast.signatures`:
  - `density_signature` — zone persons-per-m² mapped to
    the Helbing four-band scale (comfortable / dense /
    near-critical / critical).
  - `flow_signature` — unidirectional compaction into
    choke points; the classic crush-precursor pattern.
  - `pressure_wave` — RMS pressure propagation through
    the zone; the highest-confidence crush-precursor
    signal.
  - `medical_in_crowd` — anonymous collapsed-person
    candidate rate normalised by zone population.
- `triage4_coast.coast_safety`:
  - `coast_safety_bands` — Helbing 2007 + Fruin 1971
    reference defaults, tunable per zone.
  - `coast_safety_engine.CoastSafetyEngine.review(venue_id,
    zones)` → `VenueReport`.
- `triage4_coast.sim`:
  - `synthetic_coast` — deterministic multi-zone fixture
    generator tunable across density / flow-compaction /
    pressure / medical-candidate axes.
  - `demo_runner` — `make demo` entry point.
- `tests/` — model / signature / engine coverage.

## Not built

- **Person detector + tracker.** Upstream responsibility.
  This library consumes already-derived zone totals and
  flow vectors.
- **Density-map generation.** Consumer apps render the
  heat-map; the library produces per-zone scores.
- **Venue-ops dashboard.** The library produces
  `VenueOpsAlert` records; the UI + PA + radio tone
  integration lives downstream.
- **Crush-precursor simulator training.** PED-SIM /
  JuPedSim data-generation is out of scope.
- **Face recognition.** Explicitly not built. See the
  privacy boundary.
- **Per-venue calibration.** Thresholds are Helbing /
  Fruin reference numbers; real venues tune per
  geometry + event type.

## Scope boundary (repeated for emphasis)

- **Clinical:** never diagnoses medical events in
  collapsed-candidate flags.
- **Operational:** never evacuates, closes gates, or
  triggers the PA system.
- **Privacy:** zone-level only; no face-rec; no
  per-person identity.
- **Dignity:** anonymous flags; no "person in red
  shirt" characterisation.
- **Labor-relations:** no security-staff performance
  metrics derived from these signals.
- **Panic-prevention (NEW in this sibling):** alert
  vocabulary is physical (density / flow / pressure
  score), never characterising ("stampede imminent",
  "crush in progress", "catastrophic") — dramatic
  framing is itself a hazard when amplified through
  venue-ops channels.

Crossing any of the six lines is a separate product.

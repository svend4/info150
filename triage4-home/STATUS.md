# triage4-home — status

Honest accounting. Marketing language stays out of this file.

## Built

- Package scaffold (`pyproject.toml`, `Makefile`, `.gitignore`).
- `docs/PHILOSOPHY.md` — the four-boundary posture
  (clinical + operational + privacy + dignity) and the
  forbidden-vocabulary lists.
- `triage4_home.core`:
  - `enums`: `AlertLevel` (ok / check_in / urgent),
    `AlertKind` (fall / activity / mobility / baseline),
    `RoomKind` (bedroom / bathroom / kitchen / living /
    hallway / outside), `ActivityIntensity` (resting /
    light / moderate / unknown).
  - `models`: `ImpactSample`, `ActivitySample`,
    `RoomTransition`, `ResidentObservation`, `WellnessScore`,
    `CaregiverAlert` (with quadruple claims guard), `HomeReport`.
- `triage4_home.signatures`:
  - `fall_signature` — impact magnitude × post-impact
    stillness duration, with a "needs-review" band that
    flags ambiguous impacts rather than over-calling.
  - `activity_pattern` — fraction of the observation day
    spent resting / light / moderate, combined into an
    ADL-deviation score relative to a tunable baseline.
  - `mobility_pace` — estimated walking speed from room-
    transition distances + timestamps. Returns the median
    pace for the day + a trend slope across the window.
- `triage4_home.home_monitor`:
  - `fall_thresholds` — impact / stillness cut-offs wrapped
    in a tunable dataclass (defaults from Bourke 2007 +
    ISO 22537-1:2023 reference numbers).
  - `monitoring_engine.HomeMonitoringEngine.review(resident,
    observation, baseline=None)` → `WellnessScore` + alerts.
- `triage4_home.sim`:
  - `synthetic_day` — deterministic one-day-of-home
    observation generator. Tunable across fall / activity
    deviation / mobility-decline axes.
  - `demo_runner` — entry point for `make demo`.
- `tests/` — tests across models, signatures, and engine.

## Not built

- **Per-resident long-term baseline store.** Baselines are
  computed on whatever history the caller supplies. A
  retention-policy-aware baseline store with HIPAA / GDPR
  review lives in a consumer application, not here.
- **Multi-resident support.** Every observation is
  single-resident by construction. Couples living together
  need a different architecture with a different consent
  flow; explicitly out of scope.
- **Emergency-dispatch integration.** The library produces
  caregiver alerts, NOT 911 / 112 / medical-alarm-provider
  calls. Direct dispatch requires conservative thresholds
  + human-in-the-loop, both out of MVP scope.
- **Video / audio ingestion.** The library works over
  already-abstracted sensor events (impact samples, room
  transitions). Raw video / audio storage would cross the
  privacy boundary and is out of scope.
- **Medication monitoring.** Alerts deliberately do NOT
  mention medications. "Did not visit the medicine cabinet
  today" is phrased as an activity-pattern deviation, never
  a clinical medication compliance claim.
- **Real-world calibration.** Thresholds (impact 2.0 g, 
  stillness 8 s, mobility decline 15 %) come from the Bourke
  2007 / Studenski 2011 / ISO 22537 literature. Treat them as
  protocol-authentic baselines, not field-validated.

## Scope boundary (repeated for emphasis)

- **Clinical:** never diagnoses cognitive, neurological, or
  physical conditions.
- **Operational:** never dispatches emergency services
  directly. Alerts stop at "caregiver: look into it".
- **Privacy:** single-resident, no identity persisted across
  sessions, no video / audio in scope.
- **Dignity:** never pathologizes normal aging. Alert
  vocabulary describes deviations from the resident's own
  baseline, not deficits against a "healthy-adult" norm.

Crossing any of the four lines is a separate product with
separate regulatory framing. Don't erode them inside one
codebase.

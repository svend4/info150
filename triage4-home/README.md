# triage4-home

In-home elderly monitoring — **fifth sibling** in the triage4
monorepo after `triage4-fit`, `triage4-farm`, `triage4-rescue`,
and `triage4-drive`. Applies the decision-support pipeline
from `triage4` to continuous monitoring of an adult resident in
their own home.

Domain framing comes from the
[elderly home monitoring](../docs/adaptations/06_elderly_home.md)
adaptation study.

## What it is

- A library that consumes fall / activity / mobility
  observations from a home sensor hub (passive infrared,
  depth camera, wearable pendant) and emits:
  - **Fall candidate** flags (impact magnitude + post-impact
    stillness window, the standard two-factor fall-detection
    pattern).
  - **ADL deviation** scores — how far today's activity
    pattern drifts from a baseline learned over prior
    observation windows.
  - **Mobility-pace** trend — estimated walking-speed
    trend across rooms. Decline is a well-established
    frailty / wellness predictor (Studenski 2011).
- A `HomeMonitoringEngine` that weights the three channels,
  applies baseline adjustments per-resident, and produces
  **caregiver cues** — short advisory messages that a family
  caregiver or care coordinator reads on a shared dashboard.
- A deterministic synthetic home-day generator so tests and
  demos run without any real resident footage — which is
  extremely privacy-sensitive and cannot be committed to a
  repo.

## What it is not

- **Not a medical device.** Does not diagnose dementia,
  Alzheimer's, Parkinson's, dehydration, infection, or any
  other clinical condition. An unusual activity pattern
  may suggest any of those OR a house-guest visit OR a
  change in daily routine — this library cannot tell which.
- **Not an emergency-dispatch system.** It produces a
  caregiver alert when a fall candidate is detected. The
  decision to escalate to 911 / 112 / a medical alarm
  provider stays with the caregiver (or an automated
  layer OUTSIDE this library with its own false-positive
  budget).
- **Not a surveillance tool.** Movement patterns are read
  at a room-transition level, not a behavioural-detail
  level. No video storage. No audio capture. The library
  operates on already-abstracted movement events.
- **Not an identity system.** Single-resident mode by
  construction. If the resident has a family visitor,
  visitor activity is excluded upstream — this library
  does not attempt to distinguish them.

## Vocabulary translation from triage4

| triage4 (battlefield)          | triage4-home (in-home)            |
|--------------------------------|-----------------------------------|
| `CasualtyNode`                 | `ResidentObservation`             |
| `triage_priority` (1-4)        | `AlertLevel` (ok / check_in / urgent) |
| `RapidTriageEngine`            | `HomeMonitoringEngine`            |
| `MortalThresholds`             | `FallThresholds` (impact + stillness) |
| `MedicHandoff`                 | `CaregiverAlert`                  |
| "medic"                        | "caregiver"                       |
| "battlefield"                  | "residence" / "day"               |

## Four boundaries, not three

triage4-home is the first sibling where **dignity** is its
own boundary alongside clinical / operational / privacy. The
claims guard on `CaregiverAlert` enforces all four at the
dataclass level. See `docs/PHILOSOPHY.md` for rationale.

In short: alert text must not pathologize normal aging, must
not diagnose, must not dispatch emergency services directly,
and must not re-identify the resident across systems.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4`,
`triage4-fit`, `triage4-farm`, `triage4-rescue`, or
`triage4-drive`. Same rationale as the other siblings.

With five siblings now, the `DOMAIN_ADAPTATIONS §7` extraction
conversation around `biocore/` has enough data points to
finally answer what is genuinely shared (unit-interval
scoring, claims-guard pattern, dataclass shape) vs. what
just LOOKS shared but diverges in posture. Not yet the job
of this sibling; the job is getting the fifth copy-fork
right.

## See also

- `docs/PHILOSOPHY.md` — the four-boundary posture.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/06_elderly_home.md`](../docs/adaptations/06_elderly_home.md)
  — parent adaptation study.

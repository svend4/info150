# triage4-drive

In-cab driver monitoring — drowsiness, distraction, and
sudden-incapacitation detection for fleet vehicles. **Fourth
sibling** in the triage4 monorepo after `triage4-fit`,
`triage4-farm`, and `triage4-rescue`. Applies the decision-
support pipeline from `triage4` to a single-occupant moving
platform with a very different regulatory and privacy posture.

Domain framing comes from the
[driver monitoring](../docs/adaptations/13_driver_monitoring.md)
adaptation study.

## What it is

- A library that consumes eye-state, gaze-direction, and
  posture observations from a cab-mounted camera and emits:
  - **PERCLOS** (percentage of eyelid closure) — the standard
    drowsiness signal per NHTSA / SAE J2944.
  - **Distraction index** — fraction of time the driver's
    gaze is off-road beyond a grace window.
  - **Incapacitation flag** — sudden loss of postural tone
    combined with prolonged eye closure.
- A `DriverMonitoringEngine` that weights the three signals,
  applies per-driver baseline adjustments, and produces
  **dispatcher cues** — short advisory messages that a fleet
  dispatcher surfaces to the driver or operator. Cue text is
  guarded at the dataclass level by a **triple claims guard**
  (clinical / operational / privacy). See `docs/PHILOSOPHY.md`.
- A deterministic synthetic cab-session generator so tests
  and demos run without any real driver footage — which is
  extremely privacy-sensitive and cannot be committed to a
  repo.

## What it is not

- **Not a medical device.** It does not diagnose drowsiness
  disorders, strokes, arrhythmias, or intoxication. An
  unusual eye-closure pattern may suggest drowsiness OR
  microsleep OR a cultural blink pattern OR a medical event
  the library has no way to distinguish. It flags; it does
  not diagnose.
- **Not a vehicle-control system.** It never issues brake,
  steering, or acceleration commands. The operational action
  space stops at "alert the driver / dispatcher". Crossing
  into vehicle control crosses into UN-ECE R79 / FMVSS 126
  regulation and needs a different codebase.
- **Not an identity system.** It does not store face prints,
  biometric templates, or anything that can re-identify a
  specific driver. All observations are ephemeral time-series
  in normalised coordinates. BIPA-compliant by construction.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-drive (fleet)              |
|---------------------------------|-----------------------------------|
| `CasualtyNode`                  | `DriverObservation`                |
| `triage_priority` (1-4)         | `AlertLevel` (ok / caution / critical) |
| `RapidTriageEngine`             | `DriverMonitoringEngine`           |
| `MortalThresholds` (combat HR)  | `FatigueBands` (PERCLOS cut-offs) |
| `MedicHandoff`                  | `DispatcherAlert`                  |
| "medic"                         | "dispatcher"                       |
| "battlefield"                   | "cab" / "route"                    |

## Privacy posture

This is the first sibling where **privacy is a first-class
engineering concern**:

- Only normalised coordinates + unit-interval scores leave
  the library. No pixel data, no face embeddings, no
  biometric templates.
- The claims guard on `DispatcherAlert` rejects any text that
  attempts to identify the driver ("driver John", "same
  driver as last shift") because it would push the library
  across the BIPA / GDPR line.
- Per-driver baselines are **session-scoped** by default —
  they expire when the cab session ends. A future
  fleet-level baseline store belongs in a consumer
  application, not here, with its own retention policy.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4`, `triage4-fit`,
`triage4-farm`, or `triage4-rescue`. Same rationale as the
other siblings — premature `biocore/` extraction before enough
siblings converge on a real shared API hurts more than it
helps. With four siblings now, `DOMAIN_ADAPTATIONS §7`
flags the extraction conversation as newly tractable —
though not yet the job of this sibling.

## See also

- `docs/PHILOSOPHY.md` — the triple claims guard (clinical
  / operational / privacy) and why privacy requires a
  separate boundary here.
- `STATUS.md` — honest accounting of what's built.
- [`docs/adaptations/13_driver_monitoring.md`](../docs/adaptations/13_driver_monitoring.md)
  — parent adaptation study.

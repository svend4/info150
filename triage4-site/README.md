# triage4-site

Industrial / construction site safety monitoring — **sixth
sibling** in the triage4 monorepo after `triage4-fit`,
`triage4-farm`, `triage4-rescue`, `triage4-drive`, and
`triage4-home`. Applies the decision-support pipeline from
`triage4` to worker safety on fixed job sites: construction,
mining, warehouses, offshore rigs.

Domain framing comes from the
[industrial safety](../docs/adaptations/07_industrial_safety.md)
adaptation study.

## What it is

- A library that consumes already-classified site-sensor
  events (PPE detections, lifting-posture samples, thermal
  readings, fatigue-gait samples) from multi-camera hubs +
  worker wearables and emits:
  - **PPE-compliance scores** — fraction of observation
    window with required items detected.
  - **Unsafe-lifting flags** — back/hip angles at peak lift.
  - **Heat-stress proxy** — skin-temp vs. ambient differential
    combined with slowed movement, per ACGIH TLV / NIOSH
    heat-stress literature.
  - **Fatigue-gait score** — pace decline + asymmetry trend
    across the shift.
- A `SiteSafetyEngine` that weights the four channels, applies
  site-conditions adjustments (dust, rain scale down
  confidence), and produces **safety-officer alerts** that
  surface to the site safety officer — never to the worker
  directly, never to HR, never as a productivity metric.
- A deterministic synthetic shift generator so tests and demos
  run without proprietary site footage (which is NDA-locked
  and privacy-sensitive).

## What it is not

- **Not a medical device.** Does not diagnose dehydration,
  heat stroke, musculoskeletal injury, or any clinical
  condition. It flags observation patterns; a medical
  judgement is a physician's job.
- **Not a chain-of-command tool.** Alerts do not stop work,
  shut down the site, send workers home, or trigger
  discipline. The site safety officer decides operational
  actions.
- **Not a productivity / HR metric.** A core architectural
  commitment — see `docs/PHILOSOPHY.md` on the labor-
  relations boundary. Per-worker performance numbers never
  leave the library; alerts aggregate to hot-zone /
  crew-level signals.
- **Not an identity system.** Worker IDs are opaque RFID-
  badge tokens supplied by upstream; the library never
  attempts face-recognition or cross-shift identity
  matching.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-site (industrial)        |
|--------------------------------|----------------------------------|
| `CasualtyNode`                 | `WorkerObservation`              |
| `triage_priority` (1-4)        | `AlertLevel` (ok / watch / urgent) |
| `RapidTriageEngine`            | `SiteSafetyEngine`               |
| `MortalThresholds`             | `SafetyBands`                    |
| `MedicHandoff`                 | `SafetyOfficerAlert`             |
| "medic"                        | "safety officer"                 |
| "battlefield"                  | "site" / "shift"                 |

## Five boundaries

triage4-site is the first sibling where **labor relations**
is its own boundary alongside clinical / operational /
privacy / dignity. The claims guard on `SafetyOfficerAlert`
enforces five forbidden vocabulary lists at the dataclass
level. See `docs/PHILOSOPHY.md`.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4` or any other
sibling. With six siblings now, the shared-core surface is
becoming clearly visible — but the extraction work belongs
in a separate PR, not this sibling's scope.

## See also

- `docs/PHILOSOPHY.md` — the five-boundary posture.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/07_industrial_safety.md`](../docs/adaptations/07_industrial_safety.md)
  — parent adaptation study.

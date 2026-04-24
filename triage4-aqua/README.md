# triage4-aqua

Pool / beach drowning-detection support — **eighth sibling**
in the triage4 monorepo after `triage4-fit`, `triage4-farm`,
`triage4-rescue`, `triage4-drive`, `triage4-home`,
`triage4-site`, `triage4-crowd`. Lowest code reuse of any
sibling in the catalog (≈ 35 %) because water physics and
underwater perception diverge sharply from the stand-off
visible-light pipeline that powers triage4.

Domain framing comes from the
[pool / beach safety](../docs/adaptations/11_pool_beach_safety.md)
adaptation study.

## What it is

- A library that consumes already-extracted surface pose +
  submersion + swimmer-presence samples from a pool or
  beach sensor hub and emits:
  - **Submersion-duration** scores — longest run of
    consecutive below-surface samples, mapped against the
    4–6 minute drowning window.
  - **IDR posture** scores — instinctive-drowning-response
    pattern (vertical body, head low, non-rhythmic
    splashing), Wiki 2010 / Pia 2006 literature.
  - **Absent-swimmer** flags — a swimmer that entered the
    zone but hasn't surfaced and hasn't exited.
  - **Surface-distress** signals — pre-submersion IDR
    visible above water.
- A `PoolWatchEngine` that fuses the four channels into a
  unit-interval wellness score per swimmer and emits
  **lifeguard alerts** addressed to a specific guard
  pendant / smartwatch.
- A deterministic synthetic pool-session generator so
  tests and demos run without real drowning footage —
  which is ethically and legally ungatherable at scale.

## What it is not

- **Not a replacement for lifeguards.** This is the
  single most important product-positioning requirement
  per the parent adaptation file. Deployment contracts
  MUST forbid lifeguard-ratio reductions driven by this
  system. The library's output language reinforces this
  architecturally — see the **no-false-reassurance**
  claims-guard boundary.
- **Not a medical device.** It does not diagnose cardiac
  arrest, secondary drowning, or any clinical condition.
  The library flags observation patterns; medical
  diagnosis is an EMT / physician's job.
- **Not a 911-dispatch system.** The library alerts the
  lifeguard on watch via their pendant. The lifeguard,
  following venue protocol, decides whether to escalate
  to EMS. Contracts must be clear: the system supports
  lifeguards, never replaces them, never dispatches EMS
  directly.
- **Not a surveillance tool.** On-device processing + no
  raw-video upload + no swimmer identification are core
  deployment contracts. The library enforces the
  identification ban architecturally — no face prints,
  no bathing-suit descriptions, no age guesses, no
  biometric templates.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-aqua (pool / beach)       |
|--------------------------------|-----------------------------------|
| `CasualtyNode`                 | `SwimmerObservation` (anonymous)  |
| `triage_priority` (1-4)        | `AlertLevel` (ok / watch / urgent) |
| `RapidTriageEngine`            | `PoolWatchEngine`                 |
| `MortalThresholds`             | `DrowningBands` (submersion seconds + IDR confidence) |
| `MedicHandoff`                 | `LifeguardAlert`                  |
| "medic"                        | "lifeguard"                       |
| "battlefield"                  | "pool" / "session"                |

## Seven boundaries — no-false-reassurance is new

The claims guard on `LifeguardAlert` enforces seven
forbidden-vocabulary lists at construction time. Six are
inherited-and-specialised from the prior siblings
(clinical, operational, privacy, dignity, labor-relations,
panic-prevention). The seventh is domain-new:

- **No-false-reassurance** rejects language that *asserts*
  safety: "all clear", "pool is safe", "no drowning",
  "no incidents", "confirmed safe", "nothing to worry
  about". These phrases produce lifeguard complacency,
  which is the exact failure mode this product exists to
  prevent. The library describes *observed signals*, never
  *asserted safety*.

See `docs/PHILOSOPHY.md` for rationale on each boundary,
especially the new one.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4` or any other
sibling. Eighth concrete copy; the shared surface is now
very thoroughly mapped but extraction remains a separate
effort.

## See also

- `docs/PHILOSOPHY.md` — seven-boundary posture + the
  lifeguard-replacement-prevention product stance.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/11_pool_beach_safety.md`](../docs/adaptations/11_pool_beach_safety.md)
  — parent adaptation study.

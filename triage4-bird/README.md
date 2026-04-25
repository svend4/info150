# triage4-bird

Avian wildlife monitoring library — passive-acoustic + visual
+ thermal observations from a reserve / migration corridor.
**Twelfth sibling** in the triage4 monorepo. Acoustic-first
modality is the architectural shift; surveillance-overreach
+ audio-privacy are the new boundaries.

Domain framing comes from the
[wildlife avian](../docs/adaptations/02_wildlife_avian.md)
adaptation study.

## What's architecturally different about this sibling

1. **Acoustic-first signature suite**. Every prior sibling's
   primary signal modality has been pose / motion / vitals /
   reading-from-instrument. This sibling's primary signal is
   **already-classified bird-call samples** from an upstream
   BirdNET-class model. The signature layer reads call
   counts + per-species confidence + distress-flag rate, not
   raw waveforms.
2. **Audio-privacy boundary**. Passive acoustic monitoring on
   a populated reserve picks up human conversation. The
   library never accepts raw audio (the dataclass shape
   refuses) and the alert claims-guard rejects any voice-
   echoing vocabulary (`person said`, `voice content`,
   `conversation captured`). Voice-content removal is an
   upstream responsibility — the library operates on
   already-classified call counts.
3. **Surveillance-overreach boundary**. The parent adaptation
   file flags "detects avian flu" as a clinical / public-
   health claim the library cannot make. The claims guard
   rejects `detects avian flu`, `diagnoses HPAI`, `confirms
   outbreak`, `predicts outbreak`, `flu strain identified`.
   Output is `candidate mortality cluster — sampling
   recommended`, never `outbreak`.

## What it is

- A library that consumes already-classified
  ``CallSample`` records (species + confidence + distress
  flag), ``WingbeatSample`` records (visual wing-beat
  frequency for slow-flying / perched birds, used as a
  stand-off HR proxy), ``BodyThermalSample`` records, and
  ``DeadBirdCandidate`` flags from upstream visual
  classifiers — and emits:
  - **Call-presence safety** — species mix vs. expected
    profile.
  - **Distress-call rate** — fraction of calls flagged
    distress by upstream.
  - **Wingbeat-vitals safety** — wing-beat frequency vs.
    species reference band.
  - **Febrile-thermal safety** — body-temp anomaly proxy
    (avian-flu surveillance trigger).
  - **Mortality-cluster safety** — count of dead-bird
    candidates per station window.
- An ``AvianHealthEngine`` that fuses the channels and
  emits short ranger / ornithologist alerts.
- A deterministic synthetic-station generator.

## What it is not

- **Not a clinical diagnosis tool.** Avian-flu / HPAI
  conclusions are public-health calls, made by a
  surveillance lab on samples drawn from carcasses
  this library helps surface. The library NEVER says
  "detected avian flu".
- **Not a raw-audio processor.** Voice-detection +
  bandpass filtering live upstream. The library's
  data model refuses raw waveforms.
- **Not a migration-route reporter.** Multi-station
  aggregation lives in a downstream consumer; this
  library reports per-station per-window observations.
- **Not a ringing / banding identifier.** Cross-station
  individual-bird identity matching belongs in a
  separate ringing-database adapter, not here.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-bird (reserve)            |
|---------------------------------|-----------------------------------|
| `CasualtyNode`                  | `BirdObservation`                 |
| `triage_priority` (1-4)         | `AlertLevel` (ok / watch / urgent) |
| `RapidTriageEngine`             | `AvianHealthEngine`               |
| `MortalThresholds`              | `SpeciesAcousticBands`            |
| `MedicHandoff`                  | `OrnithologistAlert`              |
| "medic"                         | "ornithologist"                   |
| "battlefield"                   | "reserve" / "station"             |

## Boundaries summary

`OrnithologistAlert` enforces:

- **Surveillance-overreach (NEW)**: `detects avian flu`,
  `diagnoses HPAI`, `confirms outbreak`, `predicts
  outbreak`, `flu strain identified`, `epidemic
  detected`, `pandemic`.
- **Audio-privacy (NEW)**: `person said`, `voice content`,
  `conversation captured`, `human speech`, `audio of
  speaker`.
- **Field-security** (inherited from triage4-wild): no
  decimal-coord patterns, no `lat:` / `lng:` / `lon:` /
  `coordinates:` / `located at` vocabulary.
- **Clinical**: no definitive diagnosis (`is sick`, `has
  rabies`, `confirms`, `diagnosis`).
- **Operational**: no `cull birds`, `destroy nest`,
  `remove carcass`, `dispatch sampler`.
- **Reassurance** (light): no `no flu`, `all clear`.
- **Panic-prevention** (light): no `tragedy`,
  `catastrophe`, `disaster`.

See `docs/PHILOSOPHY.md`.

## Copy-fork architecture

Still copy-fork. Zero imports from any other sibling.

## See also

- `docs/PHILOSOPHY.md` — surveillance-overreach +
  audio-privacy + acoustic-first posture.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/02_wildlife_avian.md`](../docs/adaptations/02_wildlife_avian.md)
  — parent adaptation study (with overclaim-risk flag).

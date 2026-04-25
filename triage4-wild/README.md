# triage4-wild

Terrestrial wildlife conservation library — camera-trap +
drone health assessment for wild animals on reserves. **Eleventh
sibling** in the triage4 monorepo. Applies the decision-support
pipeline from `triage4` to a non-human, non-domestic subject
in a field-security-sensitive environment.

Domain framing comes from the
[wildlife terrestrial](../docs/adaptations/01_wildlife_terrestrial.md)
adaptation study.

## What's architecturally different about this sibling

Three new concerns distinct from every prior sibling:

1. **Field-security boundary**. GPS coordinates of protected
   animals (elephants, rhinos) are targets for poaching.
   The library never accepts or emits plaintext location
   data — `LocationHandle` is an opaque grid-cell or
   reserve-zone token. The claims guard on `RangerAlert`
   rejects `latitude`, `longitude`, `lat:`, `lng:`, `lon:`,
   `gps coordinates`, `coordinates:` vocabulary + any
   obvious decimal-degree pattern in alert text.
2. **Poaching-prediction overreach**. The parent adaptation
   file flags this as a risk: "don't claim to predict
   poaching events or optimise anti-poaching patrols —
   that's a different project with different ethics". The
   claims guard rejects `predict poacher`, `likely poacher`,
   `identify poacher`, `optimise patrol`, `schedule patrol
   route`, `anti-poaching operation` vocabulary.
3. **SMS-length constraint**. Ranger handoff is bandwidth-
   constrained (satcom / SMS). `RangerAlert.text` has a
   max-length check at construction — the library refuses
   to emit text that won't fit a standard 200-character
   ranger message frame.

## What it is

- A library that consumes already-classified camera-trap
  + drone observations of wild animals — species (from an
  upstream MegaDetector / iNaturalist classifier), pose
  samples, thermal samples, gait samples, an opaque
  location handle — and emits:
  - **Gait safety** score — quadruped limb-asymmetry.
  - **Thermal-asymmetry** score — wound / inflammation
    heat signatures.
  - **Postural-collapse** score — down / not-rising
    pattern distinguished from ordinary rest.
  - **Body-condition** score — emaciation indicator
    derived from frame geometry.
- A `WildlifeHealthEngine` that fuses the four channels
  with species-specific red-flag adjustments (wire-snare
  injury detection on limbs; tusk asymmetry on elephants;
  horn cracks on rhinos) and produces **ranger alerts** —
  short SMS-length texts addressed to a specific ranger
  handle via a consumer-app satcom bridge.
- A deterministic synthetic-reserve generator so tests
  and demos run without partnership-protected reserve
  footage.

## What it is not

- **Not a medical device.** Wildlife veterinary acts are
  out of scope. The library flags observation patterns
  for ranger + reserve-vet review; it never asserts a
  diagnosis.
- **Not an anti-poaching-patrol optimiser.** It does not
  predict poacher movements, recommend patrol routes,
  identify or track suspects, or ingest human-presence
  data. Those are a separate product with separate
  ethics oversight.
- **Not a GPS-collar logger.** The library consumes
  opaque location handles upstream; plaintext coordinates
  never enter the library. A downstream consumer app
  that ingests GPS-collar telemetry is responsible for
  obfuscating coordinates before passing an observation
  in.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-wild (reserve)           |
|---------------------------------|----------------------------------|
| `CasualtyNode`                  | `WildlifeObservation`            |
| `triage_priority` (1-4)         | `AlertLevel` (ok / watch / urgent) |
| `RapidTriageEngine`             | `WildlifeHealthEngine`           |
| `MortalThresholds`              | `SpeciesThresholds`              |
| `MedicHandoff`                  | `RangerAlert` (SMS-length)       |
| "medic"                         | "ranger"                         |
| "battlefield"                   | "reserve" / "pass"               |

## Claims guard summary

`RangerAlert` enforces:

- Clinical (no definitive diagnosis: "is injured",
  "has rabies", "confirms parasitic infection").
- Operational (no "intercept poachers", "deploy patrol",
  "dispatch rangers" — ranger command-and-control stays
  with the reserve management, not this library).
- **Field-security (NEW)** — no lat/lon vocabulary, no
  decimal-degree patterns, no "gps coordinates:", no
  "located at".
- **Poaching-prediction overreach (NEW)** — no "predict
  poacher", "identify poacher", "optimise patrol",
  "schedule patrol route", "anti-poaching operation".
- **Ecosystem-prediction overreach (NEW)** — no "population
  trajectory", "predict extinction", "species will",
  "conservation outcome prediction".
- Panic-prevention (light, ranger-facing): no "tragedy",
  "catastrophe".
- No-false-reassurance (light): no "herd is safe", "no
  threats detected", "all clear" — ranger attention
  remains required.
- **SMS-length cap (NEW)** — `text` must be ≤ 200 chars.

See `docs/PHILOSOPHY.md`.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4` or any
other sibling.

## See also

- `docs/PHILOSOPHY.md` — three new boundaries + SMS-
  length rationale.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/01_wildlife_terrestrial.md`](../docs/adaptations/01_wildlife_terrestrial.md)
  — parent adaptation study (with anti-poaching
  data-sensitivity risk flag).

# triage4-pet

Pre-visit pet health assessment library — **ninth sibling**
in the triage4 monorepo. Applies the decision-support
pipeline from `triage4` to 30–60 second phone videos a pet
owner uploads of their dog, cat, horse, or rabbit, and
produces a pre-visit summary for the vet.

Domain framing comes from the
[veterinary clinic](../docs/adaptations/08_veterinary_clinic.md)
adaptation study.

## What's architecturally different about this sibling

Every prior sibling had **one intended reader** for its
alerts: a trainer, a farmer, a first responder, a
dispatcher, a caregiver, a safety officer, a venue-ops
operator, a lifeguard. This one has **two**, each with
different language rights:

1. **Pet owner** (layperson).  Receives brief,
   non-clinical text that describes what was observed and
   always points toward vet consultation. Cannot receive
   clinical jargon ("arthritis", "fracture", "infection"),
   cannot receive definitive diagnoses, cannot receive
   reassurance that would let them skip a vet visit.
2. **Veterinarian** (clinical professional).  Receives a
   grounded multi-paragraph pre-visit summary with
   observation-level detail in clinical vocabulary. May
   contain terminology ("gait asymmetry suggestive of
   forelimb lameness", "tachypneic at rest") that would
   be wrong to send to the owner. Still forbidden:
   definitive diagnosis — the vet examines and decides.

The library answers this architecturally via **two output
dataclasses** — `OwnerMessage` and `VetSummary` — each with
its own claims-guard profile. They share a common raw
observation layer but the engine emits them separately
and the consumer app routes them to distinct UIs.

## What it is

- A library that consumes already-extracted pose + vitals
  + pain-behavior samples (from a consumer app wrapping
  MediaPipe / a quadruped pose model) and emits:
  - **Gait asymmetry** score — lameness indicator across
    the quadruped skeleton.
  - **Respiratory-distress** score — RR vs. species band,
    with panting-at-rest detection.
  - **Cardiac-band** score — HR vs. species band
    (cats ~140-220 bpm, dogs ~60-140 bpm, horses ~30-45,
    rabbits ~130-325 at rest).
  - **Pain-behavior** score — species-specific
    behavior-pattern count (dogs: tucked tail, hunched
    posture; cats: ear position, hiding; horses:
    weight-shifting).
- A `PetTriageEngine` that fuses the four channels per
  submission, applies per-species thresholds, and
  produces:
  - A `TriageRecommendation` (vet-only output):
    `can_wait`, `routine_visit`, `see_today`.
  - Zero-or-more `OwnerMessage` cues (owner UI).
  - A single `VetSummary` text block (vet UI).
- A deterministic synthetic-submission generator tunable
  per signal axis.

## What it is not

- **Not a medical device.** No FDA SaMD framework applies
  to veterinary products; the library still refuses to
  issue a definitive diagnosis — that's the vet's job
  after an in-person exam.
- **Not a replacement for a vet visit.** Owner-facing
  output never implies the owner can skip a visit. If
  the library is uncertain, the recommendation defaults
  to `routine_visit` and owner text always includes
  "consult your vet" framing.
- **Not a clinical telemedicine product.** It produces a
  pre-visit summary, not a synchronous video consultation.
  State-regulatory frameworks for vet telemedicine vary
  sharply (Texas vs. California vs. NY); this library
  produces async summaries that either route into a
  telemedicine product or sit on a clinic's pre-visit
  dashboard.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-pet                       |
|--------------------------------|-----------------------------------|
| `CasualtyNode`                 | `PetObservation` (species-aware)  |
| `triage_priority` (1-4)        | `TriageRecommendation` (can_wait / routine_visit / see_today) |
| `RapidTriageEngine`            | `PetTriageEngine`                 |
| `MortalThresholds`             | `SpeciesThresholds` (per-species RR/HR bands) |
| `MedicHandoff`                 | `VetSummary` (clinical reader)    |
| — (no equivalent)              | `OwnerMessage` (layperson reader) |

## Dual-audience claims guard

The `OwnerMessage` and `VetSummary` dataclasses each
enforce their own targeted forbidden-vocabulary list at
construction time:

- **`OwnerMessage`**: strict. No clinical jargon
  ("arthritis", "fracture", "infection"), no definitive
  diagnosis, no reassurance that could let the owner skip
  a visit ("your pet is fine"), no identity patterns
  (pet `firstname`).
- **`VetSummary`**: permissive on clinical vocabulary
  (vets are clinical professionals) BUT refuses
  definitive diagnosis, owner PII, and operational
  commands ("schedule this surgery").

See `docs/PHILOSOPHY.md` for the rationale and the full
forbidden lists.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4` or any
other sibling. With nine siblings now, the shared surface
is very thoroughly mapped.

## See also

- `docs/PHILOSOPHY.md` — dual-audience posture + species
  coverage + when-to-fork pathway.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/08_veterinary_clinic.md`](../docs/adaptations/08_veterinary_clinic.md)
  — parent adaptation study.

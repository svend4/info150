# triage4-pet — status

Honest accounting. Marketing stays out.

## Built

- Package scaffold (`pyproject.toml`, `Makefile`, `.gitignore`).
- `docs/PHILOSOPHY.md` — dual-audience posture,
  owner-facing vs. vet-facing forbidden lists, species
  coverage + when-to-fork pathway.
- `triage4_pet.core`:
  - `enums`: `SpeciesKind` (dog / cat / horse / rabbit),
    `TriageRecommendation` (can_wait / routine_visit /
    see_today), `PainBehaviorKind` (tucked_tail /
    hunched_posture / ear_position / hiding /
    weight_shifting / panting_at_rest),
    `VideoQuality` (good / shaky / low_light / occluded).
  - `models`: `PoseSample`, `GaitSample`, `BreathingSample`,
    `VitalHRSample`, `PainBehaviorSample`, `PetObservation`,
    `PetAssessment`, `OwnerMessage` (owner-facing claims
    guard), `VetSummary` (vet-facing claims guard),
    `PetReport`.
- `triage4_pet.signatures`:
  - `gait_asymmetry` — per-species limb-asymmetry score.
  - `respiratory_distress` — species-aware RR-band +
    panting-at-rest.
  - `cardiac_band` — species-aware HR-band scoring.
  - `pain_behaviors` — per-species pain-behavior weighting.
- `triage4_pet.pet_triage`:
  - `species_profiles` — RR/HR bands + per-species
    pain-behavior weights sourced from MSD Veterinary
    Manual (2022 edition) + Merck Veterinary Manual
    reference tables.
  - `triage_engine.PetTriageEngine.review(observation)`
    → `PetReport` (triage recommendation + owner cues +
    vet summary).
- `triage4_pet.sim`:
  - `synthetic_submission` — deterministic pet-video
    generator tunable per signal axis.
  - `demo_runner` — `make demo` entry point.
- `tests/` — model / signature / engine coverage.

## Not built

- **Quadruped pose extraction.** Upstream responsibility
  (MediaPipe or similar). This library consumes
  already-extracted pose samples.
- **Species classifier.** Upstream; the library accepts
  the species as an explicit `PetObservation.species`
  field.
- **Owner mobile UX.** This library produces `OwnerMessage`
  records; the upload flow / record-your-dog-walking UX
  lives in the consumer app.
- **Vet dashboard.** This library produces `VetSummary`
  text blocks; clinic-dashboard IA lives downstream.
- **State-regulatory routing.** Some US states forbid
  vet telemedicine without prior in-person visit.
  Consumer apps gate access per jurisdiction.
- **IACUC-approved validation study.** Calibration data
  would need animal-research-ethics approval; not in
  MVP scope.
- **Exotic / large-animal / equine species beyond the
  core set.** The species enum covers dog / cat /
  horse / rabbit. Extending the list means extending the
  species_profiles + pain-behavior rules.

## Scope boundary (repeated for emphasis)

- **No definitive diagnosis.** Every signature and every
  output dataclass refuses definitive-diagnosis language
  ("the pet has arthritis"). Observations are reported;
  the vet diagnoses.
- **No delay-implication for owners.** Owner-facing text
  never implies the owner can skip or delay a vet visit
  based on this library's output. If the library is
  uncertain or the observations look fine, the default
  recommendation is still `routine_visit` and owner
  text includes a "consult your vet" prompt.
- **No reassurance for owners.** An absence of alerts
  does NOT mean "everything is fine" — just "no
  concerning signatures in this 60-second clip". The
  library never writes that out to the owner in a
  reassuring tone.
- **Dual-audience separation.** Owner-facing text is
  strictly friendlier than vet-facing text. The
  `OwnerMessage` and `VetSummary` dataclasses have
  different claims-guard profiles by design.

If a future version produces definitive diagnoses,
synchronous video consult routing, or automated
appointment scheduling, that work belongs in a separate
regulated codebase with state-specific veterinary-
telemedicine legal review.

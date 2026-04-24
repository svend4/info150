# triage4-rescue — status

Honest accounting. Marketing language stays out of this file.

## Built

- Package scaffold (`pyproject.toml`, `Makefile`, `.gitignore`).
- `docs/PHILOSOPHY.md` — the clinical-adjacent vs.
  operational-control boundary and the forbidden-vocabulary
  list for `ResponderHandoff`.
- `triage4_rescue.core`:
  - `enums`: `StartTag`, `AgeGroup`, `CueKind`.
  - `models`: `VitalSignsObservation`, `CivilianCasualty`,
    `TriageAssessment`, `ResponderCue` (with claims guard),
    `IncidentReport`.
- `triage4_rescue.signatures`:
  - `ambulation_check` — "can the casualty walk?" boolean,
    feeds the first START branch.
  - `breathing_check` — respiratory-rate band evaluation,
    with airway-reposition logic (the standard START retry
    for apneic casualties).
  - `perfusion_check` — radial pulse + capillary-refill
    reading used in the second START branch.
- `triage4_rescue.triage_protocol`:
  - `start_protocol` — deterministic 1983 START algorithm,
    exactly four output tags (immediate / delayed / minor /
    deceased). No ML.
  - `jumpstart_pediatric` — Romig 1995 JumpSTART variant,
    applied automatically for casualties < 8 yr.
- `triage4_rescue.sim`:
  - `synthetic_incident` — deterministic incident fixture,
    casualty mix tunable by severity.
  - `demo_runner` — entry point for `make demo`.
- `tests/` — 60+ tests across models, signatures, and engine.

## Not built

- **CRDT sync.** The adaptation file flags this as central for
  denied-comms operation. MVP deliberately skips it — the
  library exposes pure data structures that a downstream
  CRDT layer can wrap.
- **Family-reunification workflow.** Tracks casualties across
  hospital transfer so relatives can locate them. Requires a
  separate service and data-protection review per jurisdiction;
  out of scope for MVP.
- **Multi-organisation ACL.** Red Cross + local EMS + military
  all operating the same incident need a cross-org trust
  layer. The MVP produces data; the ACL belongs in the
  consumer application.
- **Infant triage (< 1 yr).** Explicitly refused by the
  protocol layer — a `StartProtocolError` is raised rather
  than a misleading tag. Infant MCI triage uses PTT and a
  trained paediatric first responder.
- **Integration with real drones / tablets.** No platform
  bridges. The library works on `VitalSignsObservation`
  dataclasses; production-grade sensor fusion lives
  downstream.
- **Calibration against real exercises.** No FEMA tabletop
  data has been collected. Threshold values are taken from
  the published START / JumpSTART literature and should be
  treated as protocol-authentic but not field-validated.

## Scope boundary (repeated for emphasis)

This library produces **triage tags**, not **clinical
diagnoses**, not **operational commands**. The
`ResponderHandoff` claims guard rejects vocabulary that would
erode either boundary.

If a future version produces transport-priority assignments,
hospital-routing choices, or incident-command decisions, that
work belongs in a separate sibling or downstream service with
its own regulatory framing.

## Relationship to the flagship

triage4-rescue is ~90 % conceptually downstream of triage4 —
same pipeline shape, civilian framing. Per the monorepo
anti-patterns list, this is still a **copy-fork**, not an
import. After this third sibling lands, the catalog entry in
`DOMAIN_ADAPTATIONS.md` § 7 suggests the `biocore/` extraction
conversation can finally begin — but only when all three
siblings agree on what "shared" actually means in code, not
before.

# Philosophy — four boundaries, not three

triage4-home adds a **fourth** boundary — **dignity** — that
none of the prior siblings enforce at the dataclass level.
The other three boundaries (clinical + operational + privacy)
come along from the triage4 / rescue / drive lineage; the
fourth is domain-specific.

## Why dignity is its own boundary

Elderly home monitoring operates on a population that is
almost uniquely vulnerable to product language:

- **Normal aging looks pathological.** Slower walking, more
  bathroom visits, longer mid-afternoon rests — all normal.
  An alert text that calls them "confusion" or "decline" or
  "cognitive impairment" turns routine observations into
  implied diagnoses the resident never consented to.
- **Family caregivers read these alerts.** A son seeing a
  cue that says "mother appears disoriented" absorbs that
  framing even when the underlying signal is just "she
  lingered in the kitchen 20 minutes longer than usual".
  Product language reshapes family perception in ways the
  library cannot undo.
- **Elder-care products have a track record.** Marketing
  copy from older fall-detection products used "demented",
  "incompetent", "wandering" — framings that the industry
  has since pushed back against but that still survive in
  legacy codebases. Not repeating the mistake is the
  entry fee.

The library's answer is architectural: the claims guard on
`CaregiverAlert` rejects vocabulary that pathologizes aging
before the object is constructed. Text reaching the caregiver
describes what the sensors observed relative to the
resident's own recent baseline, not what the library infers
about the resident's clinical state.

## The four forbidden lists

### Clinical

- "diagnose", "diagnosis"
- "prescribe", "medicate", "administer"
- "dementia", "alzheimer", "parkinson"
- "cognitive decline", "cognitive impairment"
- "dehydrated", "malnourished"
- "infection", "sepsis"
- "pronounced", "confirmed deceased"

### Operational

- "call 911", "call 112", "dispatch ambulance"
- "call emergency services"
- "activate medical alarm"
- "contact the paramedic"

The consumer application owns the escalation step. The
library never initiates an escalation directly because a
conservative false-positive budget is a business decision
this layer cannot make.

### Privacy

- "previous resident", "same resident as"
- "identify the resident"
- "biometric match"
- "facial print", "voice print"
- Patterns like "resident <firstname>" (heuristic guard,
  same approach as triage4-drive)

### Dignity (NEW in this sibling)

- "confused", "disoriented"
- "incompetent", "cannot care for themselves"
- "dementia patient"
- "demented"
- "wandering" — loaded clinical-ish term that used to tag
  resident movements as pathological by default
- "deteriorating"
- "senile"
- "feeble"
- "frail" — loaded clinical term; use "mobility trend"
  instead

Rationale: these tokens describe the resident, not the
observation. The library only describes observations. The
caregiver (or a medical professional on a separate
clinical-decision-support track) may use some of these
tokens in their own judgement — the library never generates
them.

## What the library DOES output

Observation-forward text scoped to the resident's own
recent baseline:

> "Resident spent 18 % of daylight in moderate activity
> today, compared with a 34 % baseline over the prior 14
> days. Caregiver: consider a check-in call."

Not:

> ~~"Resident appears to be declining — possible dementia
> onset. Call 911."~~

## What gets reused from triage4

Conceptual, not literal. Copy-fork.

- Unit-interval signature scoring.
- Weighted-fusion pattern.
- Dataclass-level claims guard (extended to four lists).
- Test conventions.
- Synthetic-fixture pattern — indispensable here because
  real in-home footage is one of the most privacy-sensitive
  data categories imaginable.

## What does NOT get reused

- Any triage / MCI tag schema.
- `MortalThresholds`, `MortalSignOverride` — replaced with
  `FallThresholds` for the impact + stillness pattern.
- `MedicHandoff` — replaced with `CaregiverAlert` that
  stops at caregiver-in-the-loop.
- The fitness "coach" framing — coaching language implies
  a corrective target the library is not qualified to set
  for an elderly resident.

## When these lines move

If a future version:

- emits medical-dispatch commands → fork
  `triage4-home-medical` with HIPAA / FDA review, or
  integrate via a downstream service you own.
- performs clinical inference (dementia screening, etc.) →
  that is SaMD territory, needs IEC-62304, belongs in a
  separate regulated codebase.
- correlates across multiple residences / residents →
  fork `triage4-eldercare-analytics` with its own
  consent + retention framework.

Don't erode any of the four boundaries inside one codebase.
Eldercare product failures are almost always boundary-
erosion failures; the architecture here is designed to
make erosion a compile-time error as far as possible.

## In short

Four boundaries. One engine. Every alert that reaches the
caregiver has survived four separate claims-guard lists.
When in doubt, describe the observation relative to the
resident's own baseline — never against a healthy-adult
norm the library has no right to assert.

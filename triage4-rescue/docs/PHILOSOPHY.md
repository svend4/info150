# Philosophy — support, not command; triage, not diagnosis

Why triage4-rescue exists as a **separate package** and why its
output surface is strictly limited to START / JumpSTART triage
tags and responder-facing hints.

## Two boundaries, not one

Unlike triage4-fit (one boundary — wellness ↔ clinical) or
triage4-farm (one boundary — observation ↔ veterinary practice),
triage4-rescue operates against **two** lines that must not be
crossed:

### Clinical boundary

The output tags (immediate / delayed / minor / deceased)
describe **triage priority**, not **medical findings**. A
START tag of "deceased" means the casualty is apneic after
airway repositioning — a resource-allocation decision, not a
clinical death pronouncement. Only a licensed physician can
pronounce death.

Forbidden clinical vocabulary in `ResponderHandoff.text`:

- "diagnose", "diagnosis" — clinical act.
- "prescribe", "dose", "administer" — clinical practice.
- "confirmed dead", "pronounced deceased" — requires an MD.
- "cause of death", "suffered a stroke" — clinical inference.

### Operational-command boundary

The cues **support** a responder's next decision; they never
command it. The first responder, the incident commander, and
the local EMS medical director own operational decisions.

Forbidden operational-command vocabulary:

- "deploy", "dispatch", "assign team" — incident-command role.
- "evacuate", "extract", "transport to hospital X" — routing
  decision.
- "establish perimeter", "clear the scene" — scene-command role.

Both lists are enforced at construction time in
`ResponderHandoff.__post_init__`. A cue containing any of
these tokens raises `ValueError` before the object exists.

## What the system DOES output

- Four START tags: `immediate`, `delayed`, `minor`, `deceased`.
  These are protocol-standard colour codes (red / yellow /
  green / black on a standardised triage-tape).
- Responder cues with observation-only, decision-hint language:

  > "Respiratory rate 32/min after airway reposition. START
  > immediate. Flag for secondary assessment."

  Not:

  > ~~"Patient has acute respiratory failure. Administer O₂
  > and transport priority 1 to County General."~~

## Why two boundaries, not one

In a wellness app, crossing the clinical boundary is a
regulatory problem (SaMD / FDA). In a disaster-response
setting, crossing the operational-command boundary is a
**coordination-failure** problem. If two responders from
different organisations both follow the cue's command, they
collide; if one responder follows it and the incident
commander disagrees, the incident fragments. Either failure
costs lives faster than a missed triage tag.

Keeping the system advisory — never commanding — forces the
incident-command human-in-the-loop architecture that civilian
mass-casualty doctrine (ICS — Incident Command System, US
FEMA; JESIP — UK Joint Emergency Services Interoperability
Principles) requires.

## What gets reused from triage4

Conceptual, not literal. Copy-fork.

- Signature-scoring conventions (unit-interval per channel).
- Weighted-fusion pattern (though START is rule-based so
  fusion is much simpler here).
- Dataclass-level claims guard (with the expanded forbidden
  list above).
- Test conventions (hypothesis-style, fixed seeds, ≥ 80 %
  coverage on the protocol layer before ship).
- Synthetic-fixture pattern (because no real disaster
  footage is ethically available at scale).

## What does NOT get reused

- Larrey battlefield baseline, DARPA gate evaluators,
  `MortalThresholds` — all military-medical.
- `triage4/docs/REGULATORY.md` — SaMD / IEC-62304 is human-
  medicine specific; civilian disaster response operates
  under humanitarian-code-of-conduct regulation (ICRC) and
  host-country emergency-response law rather than medical-
  device regulation.
- `CasualtyNode.assigned_medic` field — crosses the
  operational-command boundary. Replaced with a pure-data
  `flag_for_responder_review` flag.

## When this line moves

If a future triage4-rescue version starts producing
hospital-routing assignments, transport-priority numbers, or
incident-command decisions, that crosses into operational
command-and-control. At that point the right move is:

1. Fork **triage4-ics** as a fourth sibling, tied to the
   Incident Command System specifically.
2. Engage legal review for host-jurisdiction deployments
   (ICS is US FEMA; EU has its own frameworks).
3. Keep triage4-rescue a pure triage-support library.

Don't erode the support / command line inside one codebase.
Disaster-response coordination complexity compounds badly
when tools blur their scope.

## In short

Same decision-support *infrastructure* as triage4, one step
less operational. The system observes the casualty; the
responder applies the tag; the incident commander runs the
incident.

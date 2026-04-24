# Philosophy — five boundaries

triage4-site is the first sibling where **labor relations**
is its own boundary at the dataclass level. Workplace safety
monitoring has produced product failures and union-driven
product bans precisely because prior vendors blurred the
line between "is this work-zone getting safer?" and "is
this specific worker a liability?" The library answers
architecturally: the second question cannot be asked
without crossing a claims-guard line.

The other four boundaries (clinical + operational + privacy
+ dignity) come along from the prior siblings, each
specialised to the industrial-site domain.

## Why labor relations is its own boundary

Three empirical failure modes the boundary prevents:

1. **Discipline-pipeline leak.** Worker-safety monitoring
   data routed into HR's discipline pipeline is the
   single fastest route to a union walkout. US Teamsters
   and EU works councils have historically won bans on
   workplace-camera products that enabled this flow.
2. **Productivity metric drift.** A sensor network
   installed "for safety" that starts emitting
   per-worker productivity numbers six months later is
   the textbook bait-and-switch that triggers labor-law
   challenges (France L.1222-4, Germany BDSG § 26).
3. **Individual-performance ranking.** Even anonymised
   per-worker safety scores have been used to deny
   bonuses, schedule assignments, and shift extensions
   — a pattern that multiple jurisdictions now treat as
   pretext for discriminatory firing.

The library's architecture answers these by:

- Opaque worker IDs (RFID tokens from upstream, never
  face-prints).
- No cross-shift state at the library level.
- Alert vocabulary rejected at construction time for any
  productivity / discipline framing.
- Per-observation alerts, leaving aggregation-to-hot-zones
  as a consumer-app responsibility that a labor-relations
  review can audit before deployment.

## The five forbidden lists

### Clinical

- "diagnose", "diagnosis"
- "dehydrated", "heat stroke"
- "musculoskeletal injury", "back injury"
- "exhausted", "ill"
- "pronounced", "confirmed deceased"

Rationale: heat stress "looks like" many things; a
medical judgement is a physician's job.

### Operational

- "stop work", "shut down the site"
- "halt operations"
- "evacuate", "send worker home"
- "call 911", "dispatch ambulance", "call emergency services"

Rationale: chain-of-command is the safety officer's role.
The library's action space stops at "surfacing a signal".

### Privacy

- "same worker as", "previous worker"
- "identify the worker"
- "biometric match", "facial print"
- Patterns like "worker <firstname>" (heuristic guard).

### Dignity

- "careless", "negligent", "lazy"
- "reckless", "incompetent"
- "unfit", "unprofessional"

Rationale: alerts describe observations, not worker
character. A back-angle reading doesn't tell the library
anything about the worker's professionalism.

### Labor relations (NEW in this sibling)

- "productivity", "efficiency", "output"
- "performance metric", "performance review"
- "discipline", "reprimand", "write-up"
- "HR action", "hr notification"
- "termination", "fire the worker", "dismiss"
- "performance improvement plan", "pip"
- "bonus", "withholding bonus", "incentive penalty"
- "schedule penalty"

Rationale: every one of these phrases takes the monitoring
signal and routes it into the HR / labor-discipline
pipeline. That pipeline must stay behind a separate human
review with union representation; the library never
produces text that pre-empts that review.

## What the library DOES output

Zone / observation-level text scoped to the safety officer:

> "Zone 3 (east roof edge): three PPE-harness gaps in the
> last hour. Safety officer: consider a tailgate briefing
> before the next lift cycle."

Not:

> ~~"Worker #247 has 3 harness violations — flag for HR
> discipline."~~

## What gets reused from triage4

Conceptual, not literal. Copy-fork.

- Unit-interval signature scoring.
- Weighted-fusion pattern.
- Dataclass-level claims guard (now five lists).
- Test conventions.
- Synthetic-fixture pattern with deterministic (crc32)
  seeds — even more important here because real site
  footage is NDA-locked.

## What does NOT get reused

- Any medic / MCI vocabulary.
- `MortalThresholds` — replaced with `SafetyBands` with
  OSHA / NIOSH / ACGIH reference numbers.
- `MedicHandoff` — replaced with `SafetyOfficerAlert`
  that stops at the site safety officer and never
  initiates chain-of-command actions.

## When these lines move

If a future version:

- produces HR-actionable metrics → fork `triage4-hr` (do
  not do this without explicit multi-party labor review).
- enables face-recognition identity matching → fork
  `triage4-site-id` with BIPA / GDPR / union review.
- performs clinical diagnosis → SaMD territory, separate
  regulated codebase.

Don't erode any of the five boundaries inside one
codebase. Industrial-safety product failures have all been
boundary-erosion failures; the architecture is designed
to catch erosion at construction time.

## In short

Five boundaries. One engine. Every alert has survived five
separate claims-guard lists. If the product needs to
describe what a specific worker did and route that to HR,
that is a different product with a different regulatory
review.

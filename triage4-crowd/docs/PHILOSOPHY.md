# Philosophy — six boundaries, aggregate subject

triage4-crowd introduces **panic-prevention** as its own
claims-guard boundary. Dramatic vocabulary, when relayed
through venue-ops radios, PA systems, and ultimately the
crowd itself, has historically driven the very overreaction
it warns about. The library answers architecturally: the
dataclass rejects characterising language before the alert
exists.

It's also the first sibling whose **subject is aggregate**,
not individual. The privacy and dignity boundaries are
structural here — there is literally no individual to
identify or pathologize — so the boundary work shifts onto
neutrality + panic-prevention.

## The six boundaries, specialised to the crowd domain

### Clinical

A collapsed-person candidate in a crowd may be a medical
emergency, a fall, a person taking a break, an asleep
attendee, an intoxicated-but-otherwise-fine person, a
child sitting low. The library cannot distinguish; a
candidate flag surfaces "anonymous collapsed-person
candidate in zone X, medic review recommended", never "a
seizure in zone X". Clinical tokens ("seizure", "heart
attack", "stroke", "overdose", "dead") are rejected.

### Operational

Venue-ops handles:

- PA announcements
- Gate closures
- Evacuation
- Security dispatch

The library never tries. "Close gate B", "evacuate zone",
"stop entry" tokens are rejected. The venue safety officer
(or jurisdictional equivalent) owns every operational
action.

### Privacy

Structural: the library only accepts zone-level
aggregates + anonymous medical candidates. Face recognition
is neither supported nor accepted from upstream (the
dataclass for a medical candidate has no `person_id` /
`face_embedding` / `identity_hash` field). Forbidden
vocabulary blocks attempts to re-identify ("person in red
shirt", "same attendee as earlier").

### Dignity

Anonymous flags only. No characterising a collapsed-person
candidate by appearance / age / gender / behaviour.
"Drunk attendee", "the guy who keeps falling", etc. are
rejected.

### Labor-relations

Crowd-safety signals must not be turned into security-
staff performance metrics ("guard #12 missed a density
breach"). The library blocks phrasing that would route
signals into an HR-style flow.

### Panic-prevention (NEW in this sibling)

Three empirical failure modes this boundary prevents:

1. **Radio amplification.** Security radios repeat cue
   text. A cue saying "stampede imminent in zone C"
   becomes the radio chatter heard by dozens of staff,
   several of whom then act on that framing. Descriptive
   physics ("density rising to 5.2 p/m² in zone C")
   produces measured response; characterisation
   ("catastrophic crush forming") produces flight.
2. **Operator anchoring.** Over-dramatic language in
   tools has repeatedly been cited (Hillsborough 1989
   inquiry, Itaewon 2022 report) as contributing to
   bystander and operator paralysis. Tools that say
   "normal crowd at 5 p/m²" and tools that say "crush
   conditions at 5 p/m²" produce different operator
   behaviour on identical input.
3. **PA-system leakage.** Some venue-ops tools escalate
   alert text to the PA system. Cue text describing
   "catastrophe" gets broadcast, which causes the event
   described.

Forbidden vocabulary:

- "stampede", "stampede imminent"
- "crush" (as event characterisation — the phrase "crush
  precursor signal" is only usable in engineering
  internal docs, not in operator-facing cues)
- "disaster", "catastrophe", "catastrophic"
- "fatality", "fatalities", "dead", "deceased"
- "panic" (the word itself spreads the thing)
- "mass casualty", "mass-casualty event"
- "immediate danger", "imminent danger"
- "lethal", "deadly"

Rationale: describe physics + surface a zone. Leave
characterisation to the humans with training in their
specific incident-command framework.

## Neutrality — crowd type is not the library's concern

triage4-crowd is deployment-neutral across concert crowds,
transit crowds, religious crowds, and protest crowds.
Language like "protesters", "demonstrators", "fans",
"worshippers" would characterise the crowd's intent and
is out of scope — the library sees density, flow, and
pressure. It does not classify who a crowd is.

Consumer apps that want to route signals differently
based on event type (a protest vs. a concert) make that
decision downstream, with the event-type tag as an
explicit input that the library does not need.

## What the library DOES output

Physics-forward text scoped to the joint venue safety
team:

> "Zone C density rising: 5.2 p/m² over the last 3 min,
> above the near-critical band. Flow into the zone is
> uni-directional. Venue-ops: consider metering entry
> at gate C2."

Not:

> ~~"Catastrophic crush imminent in zone C — stampede
> forming — evacuate immediately.~~"

## What gets reused from triage4

Conceptual, not literal.

- Unit-interval scoring.
- Weighted-fusion pattern.
- Claims-guard dataclass shape (now six lists).
- Test conventions, deterministic crc32 seeds.

## What does NOT get reused

- Individual vitals / pose signatures.
- `MortalThresholds` — replaced by `CrowdSafetyBands`
  (Helbing / Fruin reference cut-offs).
- Per-person tracking — not supported, by design.

## When these lines move

If a future version:

- integrates face recognition → FORK as a separate
  product line with EU AI Act / state-biometric review.
  Do not erode inside this codebase.
- produces operator-command output → fork `triage4-ops`
  for venue incident command; separate regulatory
  framing.
- distinguishes crowd by intent (protest / concert /
  etc.) → fork `triage4-event-classifier`; never inside
  this sibling.

## In short

Six boundaries. Aggregate subject. Physics vocabulary
only. When in doubt, describe the signal, not the event.

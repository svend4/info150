# Philosophy — seven boundaries, lifeguard-first posture

triage4-aqua introduces **no-false-reassurance** as its
own claims-guard boundary. Pool-safety products have
failed more often via lifeguard complacency than via
under-sensitive detection — a missed drowning with a
detection product installed invokes the worst of both
worlds (false reassurance + wrongful-death exposure).
The library answers architecturally: the dataclass
rejects language that *asserts* safety at construction
time.

The other six boundaries are inherited from the prior
siblings and specialised to the aquatic-safety context.

## Why no-false-reassurance is its own boundary

Three empirical failure modes this boundary prevents:

1. **Complacency cascade.** A dashboard that prominently
   says "Pool: ALL CLEAR" shifts lifeguard attention away
   from the water. If the product misses a drowning,
   that displacement is part of the causal chain.
2. **Contract-scope creep.** A hotel GM reading "system
   confirms pool is safe" in product marketing starts
   treating it as sufficient oversight, then reduces
   lifeguard staffing. The library's alert vocabulary is
   the first line of defence against this creep.
3. **Liability framing.** A missed drowning where the
   dashboard showed "ALL CLEAR" moments before is not
   just a false negative — it is evidence of
   false-reassurance. Plaintiff's counsel will read the
   alert text in court. The library never writes a line
   that could be quoted against a lifeguard.

## The seven forbidden lists

### Clinical

- "diagnose", "diagnosis"
- "cardiac arrest", "heart attack", "stroke"
- "secondary drowning", "dry drowning"
- "hypoxia", "hypoxic"
- "pronounced", "confirmed deceased"

Rationale: a swimmer submerged with no spontaneous
surface is a signal, not a clinical state. A drowning may
lead to any of these conditions but the library cannot
determine which — medical diagnosis is a paramedic /
physician's job.

### Operational

- "call 911", "call 112", "dispatch ambulance"
- "call emergency services"
- "perform cpr"
- "begin chest compressions"
- "defibrillate"

Rationale: the library's action space is "ping the
lifeguard's pendant". The lifeguard, following venue
protocol, handles escalation. "Perform CPR" is a
medical intervention even if the lifeguard is trained
to do it — the library never instructs clinical action.

### Privacy (child-safety-strict)

- "child in red", "child wearing"
- "boy in swimsuit", "girl in swimsuit"
- "female swimmer", "male swimmer"
- "approximate age", "looks about"
- "biometric match", "facial print"
- Patterns like "swimmer <firstname>".

Rationale: cameras + children + bathing suits = the
highest-sensitivity privacy context in the catalog. The
library never characterises a swimmer's appearance, age,
or gender. Anonymous tokens only.

### Dignity

- "drowning victim"
- "the swimmer who drowned"
- "overweight swimmer", "unfit swimmer"
- "nonswimmer" (as swimmer characterisation — using it
  to describe a specific person is blocked; the phrase
  "swimmer in nonswimmer zone" would not contain this
  token).

Rationale: alerts describe observations ("swimmer in zone
X, submersion 42 s"), not swimmer characterisations.

### Labor-relations

- "lifeguard performance", "lifeguard performance metric"
- "lifeguard missed"
- "lifeguard discipline"
- "lifeguard reprimand"
- "lifeguard write-up"

Rationale: the system supports lifeguards; deriving
performance metrics from the signal directly undermines
the union / association stance on camera-based monitoring
of lifeguard attention. Consumer apps MUST NOT build
such metrics from the library's output.

### Panic-prevention

- "tragedy", "tragic"
- "disaster", "catastrophe", "catastrophic"
- "fatality", "fatalities"
- "mass casualty"
- "lethal", "deadly"
- "victim count"

Rationale: even in time-critical rescue, dramatic language
relayed through lifeguard radios produces the very
overreaction that can lead to a rescuer becoming a second
drowning victim. Describe the signal. Let the lifeguard
act.

### No-false-reassurance (NEW in this sibling)

- "all clear"
- "pool is safe", "beach is safe"
- "no drowning", "no drowning detected"
- "no incidents"
- "all swimmers safe"
- "no risk"
- "confirmed safe"
- "system confirms safety"
- "nothing to worry about"
- "rest assured"

Rationale: the library asserts observations, never
safety. A window with no drowning-signature observations
is described as "no drowning signature in this cycle"
or "quiet window" — framed as an observation window,
not as a safety guarantee. The consumer app's UI must
never display "ALL CLEAR" as a summary of this library's
output, and the library's text refuses to provide source
material that would.

## What the library DOES output

Observation-forward text scoped to the on-watch lifeguard:

> "Swimmer 3B zone DEEP-END: submersion 42 s across
> this window, IDR posture confidence 0.78.
> Lifeguard: immediate attention warranted."

Not:

> ~~"Pool: ALL CLEAR. No drowning detected."~~
> ~~"Call 911 and begin CPR — drowning confirmed."~~

## What gets reused from triage4

Conceptual, not literal.

- Unit-interval scoring.
- Weighted-fusion pattern.
- Claims-guard dataclass shape (now seven lists).
- Test conventions, deterministic crc32 seeds.
- Synthetic-fixture pattern — critical here because
  real drowning footage cannot be ethically or legally
  gathered at scale.

## What does NOT get reused

- Larrey baseline / MortalThresholds — underwater
  physiology is wholly different.
- Existing fusion weights — aquatic channels have a
  different mortal-sign-override pattern: submersion
  duration past the critical band dominates regardless.
- Existing privacy lists — aquatic privacy is child-
  safety-strict and requires a separate, stricter list.

## When these lines move

If a future version:

- produces EMS-dispatch commands → fork `triage4-aqua-ems`
  with jurisdictional EMS-protocol review. Do not erode
  inside this codebase.
- stores swimmer identifiers across sessions → fork
  `triage4-aqua-attendance`; child-safety legal review
  required.
- produces lifeguard performance metrics → fork
  `triage4-aqua-staffing`; labor-relations review
  required.

Don't erode any of the seven boundaries inside one
codebase. Aquatic-safety product failures have almost
all been product-positioning failures; the boundary
architecture is the first line of defence.

## In short

Seven boundaries. Anonymous swimmer tokens. Observation-
forward vocabulary. The lifeguard is the product; the
library is a pendant buzz that never pretends to be
certain of the thing only a human eye can verify.

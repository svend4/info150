# Philosophy — surveillance-overreach, audio-privacy, acoustic-first

triage4-bird's distinctive contribution is a shift in primary
signal modality (acoustic, not visual) plus two new boundaries:
surveillance-overreach + audio-privacy. The acoustic-first
modality reshapes what a "signature" looks like in this
sibling; the two new boundaries respond to the parent
adaptation file's risk-flag list directly.

## Surveillance-overreach boundary

### Why it's load-bearing

The parent adaptation file flags this as risk 9.3:
"'Detects avian flu' is not a clinical claim the system can
make — it flags candidate mortality events for human-led
sampling. Language in the handoff payload must reflect this
strictly."

A bird carcass + an elevated species-call-distress rate is a
candidate mortality cluster, NOT a flu outbreak. Distinguishing
the two is the single most important architectural commitment
of this library.

### What it rejects

`OrnithologistAlert` rejects:

- `detects avian flu`, `detects hpai`
- `diagnoses avian flu`, `diagnoses hpai`
- `confirms outbreak`
- `predicts outbreak`
- `flu strain identified`
- `epidemic detected`
- `pandemic`
- `h5n1`, `h7n9`, `h5n8` (specific strain names)

### What it allows

- `candidate mortality cluster — sampling recommended`
- `elevated dead-bird-candidate rate this window`
- `species call mix shifted from baseline`

The `mortality_cluster` alert kind exists specifically to
let the engine surface "humans should sample this" without
sliding into "we diagnosed this".

## Audio-privacy boundary

### Why it's load-bearing

Risk-flag 9.2 in the adaptation file: "Passive acoustic
monitoring in populated areas picks up human conversations.
Calibration must explicitly mute / discard voice
frequencies."

The library's response is structural: it does not accept raw
audio at all. The data model only takes already-classified
`CallSample` records. Voice-content discard is therefore an
upstream responsibility — by the time data reaches this
library, voice has already been filtered.

### What it rejects in alert text

`OrnithologistAlert` text guard rejects voice-quoting
vocabulary:

- `person said`, `someone said`
- `voice content`
- `conversation captured`
- `human speech`
- `audio of speaker`
- `quoted speech`
- `transcribed audio`

### What the dataclass shape enforces

- `CallSample` only carries already-classified species +
  confidence — no audio-payload field exists in the data
  model.
- `BirdObservation` only carries `CallSample` lists,
  not raw audio.
- The library cannot accidentally process or echo voice
  content because it cannot accept it in the first place.

## Acoustic-first signal modality

Every prior sibling's primary signal has been pose / motion
/ vitals / instrument-reading. This is the first sibling
where **already-classified call counts** are the dominant
channel.

The signature suite is reorganised around acoustics:

- `call_presence` — species-mix score (calls present that
  shouldn't be, or expected calls absent).
- `distress_rate` — fraction of calls flagged distress.
- `wingbeat_vitals` — visual fallback when the bird is
  perched / slow-flying.
- `febrile_thermal` — IR signal when birds are warm.
- `mortality_cluster` — visual count of dead-bird
  candidates.

Three of those five are non-visual or visual-as-fallback —
the inverse weighting of every prior sibling. The fusion
weights reflect this: call channels collectively weight
~0.55, visual + thermal ~0.45.

## Inherited boundaries

### Field-security (from triage4-wild)

Bird-reserve coordinates can also be poaching-relevant
(rare-bird egg theft, raptor smuggling). The same regex-
based decimal-pair guard + lat / lon vocabulary guard
applies. `OrnithologistAlert` rejects coordinate leakage
in alert text.

### Clinical (no definitive diagnosis)

`is sick`, `has rabies`, `confirms`, `diagnosis` —
mirror of triage4-wild's clinical guard, applied to
avian context.

### Operational (no command actions)

`cull birds`, `destroy nest`, `remove carcass`,
`dispatch sampler` — sampling team command-and-control
stays with the surveillance lab, not this library.

### Reassurance + panic (light)

`no flu`, `all clear` rejected; `tragedy`,
`catastrophe`, `disaster` rejected. Same posture as
prior wildlife / aquatic siblings.

## What gets reused from triage4

Conceptual, not literal.

- Unit-interval signature scoring.
- Weighted-fusion pattern.
- Dataclass-level claims guard.
- Test conventions, deterministic crc32 seeds.

## What does NOT get reused

- Raw-frame perception code — the library operates above
  the upstream classifier.
- Single-modality signal weighting (visual-first); this
  sibling deliberately weights acoustic channels higher.

## When these lines move

- If a future version processes raw audio → fork
  `triage4-bird-acoustic` with explicit voice-removal
  pipeline + privacy review.
- If a future version diagnoses avian flu → that is a
  clinical claim; fork into a separate regulated codebase
  under USDA APHIS / EFSA framework.
- If a future version aggregates across stations into a
  migration tracker → fork `triage4-bird-migration` with
  ringing-database + cross-station identity work.

## In short

Acoustic-first modality. Two new boundaries —
surveillance-overreach + audio-privacy. The library
flags candidates for the human-led sampling workflow;
the lab makes the diagnosis call.

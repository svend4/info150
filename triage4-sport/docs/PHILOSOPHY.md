# Philosophy — three audiences, two new boundaries

triage4-sport extends the dual-audience pattern from
triage4-pet to **three** distinct readers and adds two new
content boundaries — injury-prediction overreach and
athlete-data-sensitivity.

## Three-audience output

A training session produces one set of observations but
flows to three readers:

- **Coach** — runs the practice. Wants form-quality +
  fatigue framing. Cannot interpret clinical vocabulary
  ("rotator cuff impingement"). The CoachMessage guard is
  strict: no clinical jargon, no definitive injury
  claims.
- **Athletic trainer** — runs warm-up, session-load
  decisions, mild rehab. Bridges coach + physician.
  TrainerNote guard is intermediate: allows ROM /
  fatigue-level vocabulary; rejects definitive diagnosis.
- **Team physician** — examines and decides. PhysicianAlert
  guard is permissive on clinical-adjacent observation
  vocabulary AND requires a non-empty `reasoning_trace`
  string (audit-readiness, copying triage4-clinic's
  positive-requirement pattern).

The library produces all three streams from one
observation. Coaches don't see the physician's clinical
detail; physicians don't see the coach's tactical
framing. Each reader gets language their role can act on.

## Universal forbidden lists (every audience)

### Injury-prediction overreach

The single most cited "marketing trap" in the parent
adaptation file: a sports-AI product saying "predicts
injury" sells well, then under-delivers and exposes the
vendor to a downstream wrongful-injury claim when an
athlete on the system gets hurt.

Every audience stream rejects:

- `predicts injury`
- `prevents injury`
- `will get injured`
- `injury imminent`
- `guaranteed safe to return`
- `ready to play` (as a clinical clearance)
- `cleared to play` (similarly)

What the library says instead: "form asymmetry persisting
above baseline this session — trainer review recommended".

### Athlete-name identifier

Same heuristic as triage4-drive / triage4-home / triage4-
pet — `athlete <firstname>` / `player <firstname>` prefix
patterns rejected.

### Team / league name leakage

A leaked output that names the team gains identifying
context. Rejected:

- `nfl`, `nba`, `nhl`, `mlb`, `mls`, `epl`,
  `premier league`, `la liga`, `bundesliga`, `serie a`
- Team-name patterns (a small representative list — real
  deployments would extend per-jurisdiction).

### Career-jeopardy framing

Career-relevant phrasing the library NEVER produces:

- `will be cut`, `roster decision`
- `will lose contract`, `contract decision`
- `marketability impact`, `marketability concern`
- `media attention warranted`

## Audience-specific forbidden lists

### CoachMessage (strict)

Clinical jargon rejected:

- `fracture`, `tear`, `sprain`, `strain` (as injury
  noun)
- `acl`, `mcl`, `pcl`, `lcl` (ligaments)
- `rotator cuff`, `meniscus`, `labrum`, `tendinitis`
- `concussion`
- `cleared to play`, `medical clearance`

Plus definitive injury claims:

- `is injured`, `has an injury`
- `confirmed injury`, `injury confirmed`
- `out for the season`

### TrainerNote (intermediate)

Allows mild rehab vocabulary (`range of motion`, `ROM`,
`fatigue level`, `RPE`, `acute load`, `chronic load`)
but rejects definitive diagnosis:

- `tear visible`, `fracture confirmed`
- `confirmed diagnosis`
- `diagnosis:`, `diagnosis is`

### PhysicianAlert (permissive on clinical, positive
audit-trace requirement)

Permits clinical-observation vocabulary the trainer
note doesn't carry — the team physician is the clinical
reader:

- `range of motion`, `flexion deficit`, `gait
  asymmetry`, `quadriceps fatigue`, `hamstring loading`,
  `plyometric readiness`

But still rejects definitive diagnosis:

- `diagnosis:`, `diagnosis is`, `confirmed diagnosis`
- `the athlete has a fracture` etc — same shape as
  triage4-clinic's diagnosis guard.

PhysicianAlert REQUIRES a non-empty `reasoning_trace`
field. The architecture mirrors triage4-clinic's
positive-requirement: any alert that reaches the
physician must carry a reproducible audit trace tying
back to the signature + threshold that drove it.

## Why this layered structure matters

Three empirical failure modes the architecture prevents:

1. **Coach over-reaction**. A coach who reads "ACL tear
   risk elevated" pulls the athlete and starts contract
   conversations. The CoachMessage guard prevents the
   library from supplying that wording in the first
   place.
2. **Trainer mis-prescription**. A trainer reading
   "diagnosis: tendinitis" may modify the rehab
   programme on what is actually just a precursor
   pattern. The TrainerNote guard refuses the diagnosis
   framing.
3. **Physician over-anchoring**. Even the team
   physician benefits from reasoning-trace accountability
   — the PhysicianAlert's required `reasoning_trace`
   forces "this alert came from signature X with value
   Y" rather than an opaque high-risk flag.

## What gets reused from triage4

- Unit-interval signature scoring.
- Weighted-fusion pattern.
- Dataclass-level claims guard (now multi-output).
- Test conventions, deterministic crc32 seeds.

## What does NOT get reused

- Single-audience output dataclass — replaced by the
  three-audience triple.
- Generous multi-paragraph format on coach / trainer
  sides (kept compact for those readers).

## When these lines move

- If a future version produces actual injury-prediction
  numerics → those crossed the marketing-trap line.
  Fork to a separate product with explicit league /
  insurance / wrongful-injury legal review.
- If a future version persists athlete identity across
  sessions → fork `triage4-sport-id` with explicit CBA
  + GDPR Art. 9 review per league.
- If a future version produces clinical clearance ("OK
  to play") → that is a SaMD-adjacent claim; fork into
  a regulated codebase.

## In short

Three audiences. Three targeted guards. Two new universal
boundaries — injury-prediction overreach and athlete-data-
sensitivity — applied across all three streams. The
PhysicianAlert inherits triage4-clinic's positive
reasoning-trace requirement; the CoachMessage and
TrainerNote inherit only negative forbidden-lists.

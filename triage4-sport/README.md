# triage4-sport

Elite-athlete sports-performance monitoring library —
**thirteenth sibling** in the triage4 monorepo. Applies the
decision-support pipeline from `triage4` to professional /
academy training-session observations.

Domain framing comes from the
[sports performance](../docs/adaptations/12_sports_performance.md)
adaptation study.

## What's architecturally different about this sibling

Three contributions distinct from every prior sibling:

1. **Three-audience output**. Extends triage4-pet's dual-
   audience pattern to three readers: a **coach** (form +
   tactics, no clinical jargon), an **athletic trainer**
   (form + workload + mild rehab vocabulary), and a **team
   physician** (clinical-adjacent observations with audit-
   trace metadata). Three output dataclasses, three
   targeted claims-guard profiles. Each reader receives
   only the language register their role can act on.

2. **Injury-prediction overreach boundary (NEW)**. The
   parent adaptation file flags injury-prediction overclaim
   as a "marketing trap" — models at best flag increased
   risk, never predict an injury. Every audience stream
   rejects `predicts injury`, `prevents injury`, `will get
   injured`, `injury imminent`, `guaranteed safe to
   return`, etc.

3. **Athlete-data-sensitivity boundary (NEW)**. Leaked
   injury status costs athletes contracts (parent file
   risk-flag 9.3). The library:
   - Operates on opaque per-session `athlete_token`
     identifiers; no cross-session identity at this layer.
   - Rejects athlete-name-prefix patterns (`athlete John`,
     `player Maria`, etc) in any output stream.
   - Rejects league / team-name vocabulary so a leaked
     output doesn't carry team-identifying context.
   - Rejects career-jeopardy phrasing (`will be cut`,
     `will lose contract`, `roster decision`,
     `marketability impact`).

## What it is

- A library that consumes already-extracted
  `MovementSample` records (sport-specific pose + form
  features), `WorkloadSample` records (GPS-vest
  workload — distance, accelerations / decelerations),
  `RecoveryHRSample` records (Eulerian HR + recovery
  rate), and a per-session `AthleteBaseline` (rolling
  baseline learned by a consumer app over weeks) and
  emits:
  - **Form-asymmetry safety** score.
  - **Workload-load safety** score (rapid-spike vs.
    rolling baseline).
  - **Recovery-HR safety** score.
  - **Baseline-deviation safety** score.
- A `SportPerformanceEngine` that fuses the channels and
  produces a `SessionReport` containing:
  - One `PerformanceAssessment` (per-channel scores +
    overall risk band).
  - Zero-or-more `CoachMessage` entries (coach UI).
  - Zero-or-more `TrainerNote` entries (trainer UI).
  - Zero-or-one `PhysicianAlert` entries (physician UI;
    only fires when athletic-rehab signals cross a higher
    threshold + carries a reasoning trace like
    triage4-clinic's audit-ready alerts).
- A deterministic synthetic-session generator.

## What it is not

- **Not a medical device.** No FDA SaMD framework. The
  library never asserts a diagnosis. PhysicianAlert text
  is observation-grounded with an audit trace.
- **Not an injury-prediction tool.** It flags precursor
  patterns for human review. Marketing-style "predicts
  injury" language is rejected at construction in all
  three output dataclasses.
- **Not a team-identity tracker.** Per-session opaque
  tokens only. Cross-session athlete identity matching
  belongs in a consumer app with explicit athlete-data-
  rights agreements (CBA / GDPR Art. 9 territory).
- **Not a contract / roster decision system.** Career-
  jeopardy framing is forbidden at the dataclass level.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-sport (training facility)  |
|---------------------------------|------------------------------------|
| `CasualtyNode`                  | `AthleteObservation`               |
| `triage_priority` (1-4)         | `RiskBand` (steady / monitor / hold) |
| `RapidTriageEngine`             | `SportPerformanceEngine`           |
| `MortalThresholds`              | `PerformanceBands`                 |
| `MedicHandoff`                  | `PhysicianAlert` (clinical reader) |
| —                               | `TrainerNote` (trainer reader)     |
| —                               | `CoachMessage` (coach reader)      |

## Boundaries summary

Each of the three audience dataclasses enforces a targeted
guard:

- **Universal across all three** (every reader): no
  injury-prediction overreach, no athlete-name patterns,
  no team / league names, no career-jeopardy phrasing.
- **`CoachMessage`** (strict): no clinical jargon
  (`fracture`, `tear`, `sprain`, `ACL`, `rotator cuff`),
  no definitive injury claims.
- **`TrainerNote`** (intermediate): allows mild rehab
  vocabulary (`ROM`, `range of motion`, `fatigue
  level`); rejects definitive diagnosis (`tear`,
  `fracture confirmed`).
- **`PhysicianAlert`** (permissive on clinical
  observation; positive-requirement audit trace):
  permits ROM / asymmetry vocabulary; rejects
  definitive diagnosis; REQUIRES non-empty
  `reasoning_trace` (audit-readiness — like
  triage4-clinic's pattern).

See `docs/PHILOSOPHY.md`.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4` or any other
sibling.

## See also

- `docs/PHILOSOPHY.md` — three-audience posture +
  injury-prediction overreach + athlete-data-sensitivity.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/12_sports_performance.md`](../docs/adaptations/12_sports_performance.md)
  — parent adaptation study.

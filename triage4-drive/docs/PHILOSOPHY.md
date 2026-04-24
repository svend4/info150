# Philosophy — three boundaries, not two

triage4-drive is the first sibling where **privacy** is a
first-class engineering boundary. The other three siblings
have one or two posture boundaries; this one has three, all
enforced at the dataclass level via the claims guard on
`DispatcherAlert`:

1. **Clinical boundary** — never diagnose, prescribe, name
   a specific medical condition.
2. **Operational-control boundary** — never command vehicle
   control. No brake / steer / accelerate instructions.
3. **Privacy boundary** — never produce text that identifies
   a specific driver, references stored biometrics, or
   compares drivers across sessions.

## Why privacy is a separate boundary here

The other siblings can get away with an "observation-only"
framing because their subjects are already non-private
(livestock in `triage4-farm`) or already handled under a
public-safety framework (civilian casualties in
`triage4-rescue`). An in-cab camera is different:

- **Biometric-law patchwork.** Illinois BIPA has produced
  multi-million-dollar class actions against facial-biometric
  products. Texas CUBI, Washington HB 1493, and EU GDPR
  Art. 9 treat face data as a regulated category.
- **Union and works-council resistance.** US Teamsters and
  EU works councils have blocked in-cab camera deployments
  that allow driver re-identification. Explicit consent +
  no-stored-biometrics is table stakes.
- **Commercial fragility.** A single BIPA judgment makes a
  product uninsurable. The privacy boundary is not
  aspirational — it's the moat.

The library's answer is architectural: **nothing that can
identify a driver leaves the library**. All observations are
normalised coordinates + unit-interval scores. No face
embeddings. No stored templates. No cross-session comparison.

## Forbidden vocabulary

### Clinical

- "diagnose", "diagnosis"
- "prescribe", "medicate", "administer"
- "drunk", "intoxicated", "under the influence"
- "stroke", "arrhythmia", "seizure", "heart attack"
- "pronounced", "confirmed deceased"

Rationale: drowsiness looks like a lot of things. Some of
them are medical events the library cannot distinguish. The
cue language is behavioural, never etiological.

### Operational-control

- "brake", "auto-brake"
- "stop the vehicle", "pull over now"
- "disengage autopilot"
- "take over"
- "steer", "accelerate"

Rationale: vehicle control is UN-ECE R79 / FMVSS 126
regulated. A library that emits a "brake" cue has crossed
into a different regulatory domain and a different product.

### Privacy / identification

- "driver X" with a specific name (pattern-matched on
  common name tokens — see models.py for the exact list)
- "same driver as"
- "matches previous driver"
- "driver identity"
- "biometric match", "facial print"
- "identify the driver"

Rationale: every one of these phrases tries to re-identify
a human across time. The library operates session-scoped
by construction and rejects any alert text that contradicts
that contract.

## What the system DOES output

Behavioural observations with a dispatcher-forward framing:

> "PERCLOS 0.34 over the last 3 min. Caution: drowsiness
> signature. Consider a driver rest break."

Not:

> ~~"Driver John is drunk — brake now and call 911."~~

## What gets reused from triage4

Conceptual, not literal. Copy-fork.

- Signature-scoring conventions (unit-interval per channel).
- Weighted-fusion pattern (PERCLOS + distraction + posture
  into a combined `FatigueScore`).
- Dataclass-level claims guard (expanded to three
  boundaries).
- Test conventions (hypothesis-style, fixed seeds,
  determinism in every signature).
- Synthetic-fixture pattern — even more critical here,
  because no real driver footage can be committed to the
  repo.

## What does NOT get reused

- Any triage / MCI vocabulary — this sibling is about
  continuous monitoring, not discrete triage tagging.
- `MortalThresholds`, `MortalSignOverride` — the analogous
  cut-offs (PERCLOS bands, distraction thresholds) live in
  `fatigue_bands.py` with NHTSA-sourced numbers, not
  Napoleonic battlefield ones.
- `MedicHandoff` — replaced by `DispatcherAlert` which
  never crosses the operational-command boundary.

## When these lines move

If a future version:

- emits vehicle-control commands → fork `triage4-drive-ads`
  for ADAS (Advanced Driver Assistance System) territory,
  with UN-ECE R79 / R157 review.
- stores facial embeddings for re-identification → fork
  `triage4-drive-id` for driver-identity territory, with
  BIPA / GDPR legal review.
- correlates across drivers / shifts → fork
  `triage4-fleet` for fleet-analytics territory.

Don't erode the three lines inside one codebase. Privacy
complexity compounds badly when a tool blurs its scope.

## In short

Same decision-support *infrastructure* as triage4. Three
posture boundaries where most siblings have one. The privacy
boundary is load-bearing — if you find yourself wanting to
add cross-session identification, stop and fork.

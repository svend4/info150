# triage4-coast

Crowd-safety monitoring for venues — stadiums, music festivals,
transit hubs, religious gatherings. **Seventh sibling** in the
triage4 monorepo after `triage4-fit`, `triage4-farm`,
`triage4-rescue`, `triage4-drive`, `triage4-home`, and
`triage4-site`. Applies the decision-support pipeline from
`triage4` to aggregate crowd state.

Domain framing comes from the
[crowd safety](../docs/adaptations/14_crowd_safety.md)
adaptation study.

## What's architecturally different about this sibling

Every prior sibling scored **an individual subject** (a
trainee, a cow, a casualty, a driver, a resident, a worker).
This sibling scores **a zone** — an area of a venue with an
aggregate crowd inside it. Three consequences flow from that:

1. The raw observations describe physics (density, flow,
   pressure), not a person's pose / vitals / PPE.
2. There is no `worker_token` / `casualty_id` / equivalent;
   the primary identifier is `zone_id`. No face recognition,
   no individual identity persisted anywhere.
3. A separate **medical-in-crowd** signal flags anonymous
   collapsed-person candidates for medic review. These
   candidates never acquire a name or identity — they are
   "a person in zone A needing review", no more.

## What it is

- A library that consumes already-derived zone-level
  measurements (counts per zone, flow vectors, pressure
  readings, anonymous collapsed-person candidates) and emits:
  - **Density scores** — per-zone density vs. safe-threshold
    maps, per Helbing et al. crowd-safety literature.
  - **Flow scores** — unidirectional compaction into choke
    points, the classic crush-precursor pattern.
  - **Pressure scores** — pressure-wave propagation through
    a crowd; the highest-confidence crush-precursor signal
    the library reads.
  - **Medical-in-crowd flags** — anonymous collapsed-person
    candidates for medic triage review.
- A `CoastSafetyEngine` that fuses the four channels per
  zone, weights by venue-area-type, and produces
  **venue-ops alerts** for the joint security + medical
  team — never commands, never triggers PA announcements.
- A deterministic synthetic-venue generator so tests and
  demos run without the sparse, legally-contested crush
  footage (Hillsborough / Love Parade / Itaewon are the
  studied cases and committing any of their footage is
  both contested and unethical at scale).

## What it is not

- **Not a surveillance tool.** No face recognition, no
  crowd-identification, no cross-event tracking. The
  parent adaptation file flags this as a core product-
  positioning requirement — accepting face-recognition
  work turns the product into surveillance tech. See
  `docs/PHILOSOPHY.md`.
- **Not an evacuation system.** It never commands a
  venue evacuation, closes gates, or triggers the PA
  system. Alert language stops at "surface to venue ops".
- **Not a crowd-control tool.** It does not tell security
  to disperse a crowd, remove attendees, or intervene. A
  crowd-safety alert goes to the venue medical / security
  team, who run the ICS-style response. The library is
  never the incident commander.
- **Not a political classifier.** It does not identify
  "protesters" vs. "concertgoers" vs. "worshippers" —
  the vocabulary is always "crowd", never characterised
  by what the crowd is doing. Same architecture for a
  music festival and for a democratic demonstration.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-coast (venue)             |
|---------------------------------|-----------------------------------|
| `CasualtyNode`                  | `ZoneObservation` (+ anonymous `MedicalCandidate`) |
| `triage_priority` (1-4)         | `AlertLevel` (ok / watch / urgent) |
| `RapidTriageEngine`             | `CoastSafetyEngine`              |
| `MortalThresholds`              | `CrowdSafetyBands` (density cut-offs + pressure bands) |
| `MedicHandoff`                  | `VenueOpsAlert`                   |
| "medic"                         | "venue-ops"                       |
| "battlefield"                   | "venue"                           |

## Six boundaries

triage4-coast adds **panic-prevention** as its own claims-
guard boundary. Dramatic vocabulary ("stampede", "crush in
progress", "disaster", "catastrophic", "immediate danger")
routed to security staff can trigger the very overreaction
that causes the injury. The library describes the physics,
not a characterisation of the event. The other five
boundaries (clinical / operational / privacy / dignity /
labor-relations) are scoped to the venue-ops context.

See `docs/PHILOSOPHY.md`.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4` or any other
sibling. With seven siblings now, the shared surface is
very clearly mapped — but extraction remains a separate
effort for later.

## See also

- `docs/PHILOSOPHY.md` — the six-boundary posture, the
  panic-prevention rationale, and the neutrality posture
  around crowd-type framing.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/14_crowd_safety.md`](../docs/adaptations/14_crowd_safety.md)
  — parent adaptation study.

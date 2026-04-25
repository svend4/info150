# triage4-fish

Aquaculture pen-welfare monitoring library — **fourteenth and
final sibling** in the triage4 monorepo. Applies the
decision-support pipeline from `triage4` to underwater
fish-farm pens (salmon, trout, sea bass, tilapia).

Domain framing comes from the
[wildlife aquatic](../docs/adaptations/03_wildlife_aquatic.md)
adaptation study.

## What's architecturally different about this sibling

Three contributions distinct from every prior sibling:

1. **Multi-modal sensor fusion**. First sibling that fuses
   vision-derived signals (gill rate, school cohesion, sea
   lice burden, mortality-floor count) with **water-
   chemistry sensor inputs** (dissolved oxygen, temperature,
   salinity, turbidity). The engine's reasoning logic
   considers cross-modal corroboration: low DO + slowed
   gill rate is a different signal pattern than slowed gill
   rate alone. The water-chemistry channel scales the
   confidence of the visible-light channels (turbid water
   → reduced vision-channel weighting), and contributes
   its own safety score independently.

2. **Antibiotic-dosing-overreach boundary (NEW)**. The
   parent adaptation file flags this directly: "Do NOT
   directly recommend dosing — flag 'consult a
   veterinarian' as the action." Salmon farms make
   antibiotic-dosing decisions every week, often under
   regulatory + commercial pressure. The library refuses
   to emit therapeutic recommendations; it surfaces
   observation patterns and routes the decision to a vet:
   - Forbidden: `administer antibiotic`, `dose with`,
     `prescribe antimicrobial`, `treatment regimen`,
     `withdrawal period`, `start oxytetracycline`,
     `florfenicol dosing`, `medicated feed`.
   - Allowed: `consult veterinarian`,
     `vet review recommended`,
     `disease-pattern signature surfaced`.

3. **Failure-cost-asymmetric no-false-reassurance posture**.
   The parent file: "If the system misses a disease
   outbreak, the farm can lose $1M+ of stock in a week.
   Under-promise." This sibling has the strongest
   no-false-reassurance posture in the catalog —
   `PenReport.as_text` for an empty alert list explicitly
   says "absence of alerts is not a clearance of pen
   welfare", and the FarmManagerAlert claims guard rejects
   `pen is healthy`, `no outbreak`, `stock is safe`,
   `clean bill of health`.

## What it is

- A library that consumes already-derived per-pen
  observations:
  - `GillRateSample` — pen-aggregate gill rate (Eulerian-
    derived) per species reference band.
  - `SchoolCohesionSample` — nearest-neighbour distance +
    polarization aggregate.
  - `SeaLiceSample` — confidence-weighted lice count
    proxy.
  - `MortalityFloorSample` — dead-fish-on-bottom count.
  - `WaterChemistrySample` — DO / temperature / salinity
    / turbidity readings from bundled pen sensors.
- An `AquacultureHealthEngine` that fuses the five
  channels into a `PenWelfareScore` with cross-modal
  corroboration and produces `FarmManagerAlert` records
  routed to the pen-management UI.
- A deterministic synthetic-pen generator.

## What it is not

- **Not a veterinary therapeutic tool.** Antibiotic /
  antimicrobial dosing decisions are veterinary
  practice. The library NEVER recommends dose,
  withdrawal period, or specific drug. It flags
  observation patterns and routes the decision to a
  vet via "consult veterinarian" framing.
- **Not an outbreak diagnosis system.** Like
  triage4-bird, the library never says "outbreak
  detected" — it says "candidate disease pattern —
  vet review recommended".
- **Not a per-fish identity tracker.** Pen-level
  aggregate by design (similar to triage4-crowd's
  zone-level subject). Per-fish identity tracking would
  cross into research-traceability territory and
  belongs in a separate codebase.
- **Not a harvest / feed-conversion calculator.** The
  library produces welfare observations, not
  commercial-yield numbers.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-fish (aquaculture)         |
|---------------------------------|------------------------------------|
| `CasualtyNode`                  | `PenObservation` (pen-aggregate)   |
| `triage_priority` (1-4)         | `WelfareLevel` (steady / watch / urgent) |
| `RapidTriageEngine`             | `AquacultureHealthEngine`          |
| `MortalThresholds`              | `SpeciesAquaticBands`              |
| `MedicHandoff`                  | `FarmManagerAlert`                 |
| "medic"                         | "farm-manager"                     |
| "battlefield"                   | "pen" / "pen-pass"                 |

## Boundaries summary

`FarmManagerAlert` enforces:

- **Antibiotic-dosing-overreach (NEW)**: as listed
  above.
- **Veterinary-practice** (inherited from triage4-farm,
  specialised for fish): no `diagnose`, `prescribe`,
  `medicate`, `therapy`, `dose `, `administer`,
  `medicated feed`, `withdrawal period`.
- **Outbreak-diagnosis-overreach** (similar to
  triage4-bird): no `outbreak detected`,
  `epidemic`, `pandemic`, `disease confirmed`. Output
  is "candidate disease pattern".
- **Field-security** (inherited from triage4-wild):
  no decimal-degree patterns, no lat/lon vocabulary
  (relevant for offshore tuna / bluefin pens which
  are theft targets).
- **No-false-reassurance** (strongest posture in the
  catalog): no `pen is healthy`, `no outbreak`,
  `stock is safe`, `clean bill of health`,
  `no concerns`, `all pens safe`.
- **Operational**: no `cull the pen`, `harvest now`,
  `move stock`, `dump the pen`.
- **Panic-prevention**: no `disaster`, `catastrophe`,
  `mass mortality`.

See `docs/PHILOSOPHY.md`.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4` or any
other sibling. **This is the fourteenth and final
copy-fork in the catalog.** With every adaptation now
implemented, the `biocore/` extraction conversation
from `DOMAIN_ADAPTATIONS §7` is grounded in fourteen
real codebases sampling every realistic combination of
boundaries / audiences / structural constraints /
positive requirements / multi-modal fusion. The
extraction work itself remains a separate commit.

## See also

- `docs/PHILOSOPHY.md` — multi-modal fusion +
  antibiotic-dosing-overreach + failure-cost-asymmetry.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/03_wildlife_aquatic.md`](../docs/adaptations/03_wildlife_aquatic.md)
  — parent adaptation study.

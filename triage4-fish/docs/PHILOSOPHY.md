# Philosophy — multi-modal fusion, antibiotic-overreach, failure-cost asymmetry

triage4-fish closes the catalog of fourteen siblings with
three contributions distinct from every prior one.

## Multi-modal sensor fusion

This is the first sibling that fuses **two distinct sensor
modalities** at the engine layer:

- **Vision-derived channels**: gill rate, school cohesion,
  sea lice burden, mortality floor.
- **Water-chemistry sensor channels**: dissolved oxygen,
  temperature, salinity, turbidity from bundled pen
  sensors.

The engine treats water chemistry as both:

1. A **confidence-scaling input**. Turbid water +
   silt-storm conditions reduce the visible-light
   channels' weights — the engine cannot see clearly, so
   it blends those channels toward neutral. Same posture
   as triage4-aqua's `pool_condition` scaling, but
   driven by a numeric chemistry sample rather than an
   enum.
2. An **independent safety channel**. Low DO + high
   temperature is a stress signal in its own right, even
   without confirming visual evidence. The
   `water_chemistry` channel score contributes to the
   weighted overall.

When a vision channel deviates AND water chemistry is
also degraded, the engine attaches a corroboration
note ("low DO co-occurring with reduced gill rate")
to the alert — surfacing the cross-modal pattern is
the architectural contribution.

## Antibiotic-dosing-overreach boundary

The parent adaptation file is explicit (risk-flag 9.3):

> "Antibiotic-dosing decisions triggered by the
> monitoring output are subject to veterinary law in
> many jurisdictions. Do NOT directly recommend dosing —
> flag 'consult a veterinarian' as the action."

Aquaculture is the domain in which this boundary is
most concrete: salmon farms make weekly antibiotic-
dosing decisions, often under regulatory + commercial
pressure. A library that emits "administer 50 mg/kg
oxytetracycline" output crosses into veterinary
practice (EU Directive 2019/6) regardless of whether
its developers intended that.

`FarmManagerAlert` rejects:

- `administer antibiotic`, `administer antimicrobial`
- `dose with`, `dosing recommendation`
- `prescribe antimicrobial`, `prescribe antibiotic`
- `treatment regimen`, `course of treatment`
- `withdrawal period`
- Specific salmon-aquaculture drug names:
  `oxytetracycline`, `florfenicol`, `emamectin`,
  `azamethiphos`, `medicated feed`

What's allowed: "consult veterinarian", "vet review
recommended", "disease-pattern signature surfaced".
The library's action surface stops at "this needs a
human with a veterinary licence to look at it".

## Failure-cost asymmetry — strongest no-false-reassurance posture

The parent file: "If the system misses a disease
outbreak, the farm can lose $1M+ of stock in a week.
Under-promise."

This sibling has the strongest no-false-reassurance
posture in the catalog because the failure cost is
both large AND asymmetric — false-reassurance produces
a single failure mode (missed outbreak → $1M loss) with
no offsetting upside ("the system said all clear" never
generates value).

`FarmManagerAlert` rejects:

- `pen is healthy`
- `no outbreak`
- `stock is safe`, `stocks are safe`
- `clean bill of health`
- `no concerns`, `no welfare concerns`
- `all pens safe`
- `no disease`
- `disease-free`

`PenReport.as_text` for an empty alert list produces
explicit observation-worded text: "absence of alerts
is not a clearance of pen welfare — vet + farm-manager
review remains required".

## Inherited boundaries

### Veterinary-practice (specialised from triage4-farm)

The standard livestock-welfare guard list applies,
specialised for fish:

- `diagnose`, `diagnosis`
- `prescribe`
- `medicate`, `medication regimen`
- `therapy`
- `dose `, `administer`
- `medicated feed`, `withdrawal period`

### Outbreak-diagnosis-overreach (from triage4-bird)

The library NEVER says "outbreak detected" / "disease
confirmed" / "epidemic" / "pandemic". Aquaculture
disease nomenclature like "ISA confirmed" (Infectious
Salmon Anemia) or "PD detected" (Pancreas Disease) is
similarly rejected — those are sampling-lab calls.

### Field-security (from triage4-wild)

Offshore tuna / bluefin pens are theft targets.
Decimal-degree coordinate patterns rejected; lat / lon /
gps-coordinates / located-at vocabulary rejected.

### Operational

The library never recommends:
- `cull the pen`
- `harvest now`
- `move stock`
- `dump the pen`

Those are commercial / vet decisions.

### Panic-prevention

`disaster`, `catastrophe`, `mass mortality` rejected —
even for a clear mortality cluster, the framing stays
"candidate mortality cluster — vet + farm-manager
review".

## What gets reused from triage4

Conceptual, not literal.

- Unit-interval signature scoring.
- Weighted-fusion pattern (extended to multi-modal
  here).
- Dataclass-level claims guard (now with five
  inherited + one new boundary list).
- Test conventions, deterministic crc32 seeds.

## What does NOT get reused

- Single-modality signal weighting — the multi-modal
  fusion is the architectural shift.
- Per-individual identity tracking — pen aggregate by
  design.

## When these lines move

- If a future version produces dosing recommendations
  → fork into a regulated veterinary-therapeutics
  codebase under EU Directive 2019/6 / FDA CVM / etc.
  Substantial.
- If a future version diagnoses specific pathogens
  (ISA, PD, IPN, SAV) → that's a sampling-lab claim;
  fork to a separate regulated codebase.
- If a future version produces commercial-yield
  numbers → that's a different product; fork
  `triage4-fish-yield` for the FCR / harvest-planning
  domain.

## In short

Three new contributions: multi-modal fusion at the engine
layer, antibiotic-dosing-overreach at the dataclass
guard, and the strongest no-false-reassurance posture in
the catalog driven by failure-cost asymmetry. The
fourteenth sibling closes the catalog with the most
domain-novel signal-fusion architecture and the most
specifically-regulated veterinary-practice boundary the
catalog covers.

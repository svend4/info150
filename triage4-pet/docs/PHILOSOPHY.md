# Philosophy — dual audience, targeted guards

triage4-pet is the first sibling whose output flows to
**two distinct readers**. That structural fact drives the
philosophy. The observation layer is shared, but the
output dataclasses diverge: `OwnerMessage` goes to a
layperson on their phone; `VetSummary` goes to a licensed
veterinarian on a clinic dashboard. Each has its own
forbidden-vocabulary profile.

## Why dual audience matters

Three empirical failure modes this architecture prevents:

1. **Layperson misinterpretation.** An owner who reads
   "possible fracture of the right forelimb" will
   frequently translate it as "my dog's leg is broken"
   and act accordingly — either with over-alarm (ER visit
   when not needed) or delay (they "diagnose" themselves
   and don't go to the vet at all). Clinical vocabulary
   is safe for a vet, unsafe for an owner. The library
   reflects this architecturally.
2. **Over-simplification for the vet.** A summary written
   for a layperson ("the video shows your dog walking
   unevenly") strips out the information a vet needs to
   plan the exam ("forelimb lameness grade 2/5, weight
   shifting toward contralateral hind, panting at rest,
   RR 42"). Vets have reported — in every study on
   veterinary AI tooling the parent adaptation file
   cites — that they don't trust tools that oversimplify.
3. **Reassurance that lets an owner skip a visit.** A
   quiet window means "no concerning signals in this 60
   s clip", not "your pet is fine". Owner UI text must
   never let the owner conclude "everything is fine" and
   skip a vet visit. This is the veterinary cousin of
   triage4-aqua's no-false-reassurance boundary, but
   with a sharper regulatory edge: owner misuse here
   produces animal-welfare harm in ways that ripple
   through insurance, liability, and state-licensure
   frameworks.

## The two forbidden lists

### OwnerMessage — strict

Owner-facing text is enforced at the dataclass level to
reject:

- **Clinical jargon**: "arthritis", "fracture",
  "infection", "malignancy", "tumor", "neoplasia",
  "cardiomyopathy", "gastroenteritis", "pancreatitis",
  "nephropathy", "hepatopathy", "osteochondrosis",
  "hypothyroidism", "hyperthyroidism", "diabetes",
  "seizure", "stroke".
- **Definitive diagnosis**: "has a", "is suffering
  from", "this is", "diagnosis:", "confirms".
- **Reassurance / delay-implication**: "everything is
  fine", "your pet is fine", "no need to worry", "no
  concerns", "safe to skip", "no vet visit needed",
  "can wait without seeing a vet", "nothing is wrong".
- **Operational commands to the owner**: "give medication",
  "administer", "prescribe".
- **Pet-identity patterns**: "<firstname>" prefix
  heuristic blocked.

### VetSummary — permissive on clinical vocabulary,
strict on diagnosis + privacy

Vet-facing text is still guarded but looser on medical
vocabulary (the vet is the clinical professional here):

- **Definitive diagnosis**: "diagnosis:", "has a
  fracture" (phrased so the library asserts ownership
  of the diagnosis — the vet hasn't examined yet; the
  library's role is grounded observation for the vet to
  interpret).
- **Operational scheduling**: "schedule surgery",
  "order this procedure", "prescribe this drug",
  "administer this medication".
- **Owner PII**: "owner name:", "owner phone",
  "owner email", "owner address". The library never
  produces owner-identifying content — that data flows
  separately through the consumer app's consent-gated
  layer.

## What the library DOES output

**OwnerMessage**: brief, non-clinical, always ends with
consult-vet framing.

> "Your dog's walking pattern looks uneven in this clip.
> Please share this with your vet — they may want to see
> your dog to take a closer look."

Not:

> ~~"Your dog has arthritis. No need to worry, a rest
> day should fix it."~~

**VetSummary**: grounded multi-paragraph with observation
detail.

> "Dog, est. 7 yr (owner-reported). 62 s clip.
> Gait: right forelimb lameness grade ~2/5, weight-
> shifting toward left hind (intermittent). Respiratory:
> RR 42 at rest, species reference 10-30 — tachypneic.
> Cardiac: HR estimate unreliable (animal not still
> enough). Pain behaviours: panting at rest, hunched
> posture intermittent. Pre-visit recommendation:
> see_today."

## Species coverage

Four species in the MVP: dog, cat, horse, rabbit. Per-
species profiles draw from the MSD Veterinary Manual
(2022) reference vitals. Extending to exotic or large-
animal species means extending `species_profiles.py`
and the pain-behavior rules. Known species under-
coverage is flagged in `STATUS.md` — owners who upload
video of an iguana should see an "unsupported species,
please contact your vet directly" message from the
consumer app, not a silently wrong assessment from this
library.

## What gets reused from triage4

Conceptual, not literal.

- Unit-interval signature scoring.
- Weighted-fusion pattern.
- Dataclass-level claims guard (now in a dual-dataclass
  configuration).
- Test conventions, deterministic crc32 seeds.
- Synthetic-fixture pattern — essential here because
  veterinary video is IACUC-gated and cannot be
  committed to an open-source repo.

## What does NOT get reused

- Human triage frameworks (START / JumpSTART are not
  veterinary).
- `MortalThresholds` — species-specific, replaced by
  `SpeciesThresholds` per species.
- Single-audience alert dataclass — replaced by the
  dual-audience `OwnerMessage` + `VetSummary` pair.

## When these lines move

- If a future version issues definitive diagnoses →
  SaMD-equivalent veterinary-regulatory review would
  apply in some jurisdictions; fork separately.
- If a future version routes directly to a synchronous
  video consultation → state-regulatory gate; fork
  `triage4-pet-telemed` per jurisdiction.
- If a future version schedules appointments →
  `triage4-pet-ops` for scheduling integration.

Don't erode the dual-audience separation inside one
codebase. The two output streams are load-bearing; the
product is coherent precisely because it refuses to
conflate the owner's UX with the vet's.

## In short

Two audiences. Two output dataclasses. Two claims-guard
lists. The observation layer is shared; the language
rights are not.

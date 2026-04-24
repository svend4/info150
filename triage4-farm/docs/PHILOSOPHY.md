# Philosophy — observation, not veterinary practice

Why triage4-farm exists as a **separate package** and why its
output surface is strictly limited to observation + referral.

## The hard boundary

triage4-farm is a **welfare-observation tool for farmers**. It
watches a herd, scores each animal on signs of welfare problems,
and generates a farmer-facing alert when a vet review is
warranted.

It is **not**:

- A veterinary diagnostic tool. Diagnosis is a licensed
  profession in every major jurisdiction (US Veterinary
  Medicine Practice Act, EU Directive 2001/82/EC, UK Veterinary
  Surgeons Act 1966). An automated system that "diagnoses" an
  animal practises veterinary medicine without a licence.
- A treatment-recommendation tool. "Administer tylosin",
  "increase anti-inflammatory dose", "start a withdrawal
  period" — all illegal for a non-veterinarian to do in the
  countries that matter for agtech commerce.
- An antibiotic-dosing assistant. Antibiotic use in food
  animals is tightly regulated (FDA VFD rule in US, EU
  Directive 2019/6). Even flagging "this animal probably needs
  antibiotics" creates liability for farmers who then dose
  without a vet prescription.

## What the system DOES output

Welfare flags and alert text end in **"vet review recommended"**
when a welfare concern is surfaced. The text describes the
observation, not a recommendation:

> "Animal #247 is showing gait asymmetry consistent with
> lameness. Vet review recommended."

Not:

> ~~"Animal #247 has lameness. Start Metacam 20 mg/kg."~~

The dataclass-level claims guard in `FarmerAlert.__post_init__`
enforces this — any alert text containing forbidden vocabulary
raises `ValueError` at construction time. Forbidden words
include (not exhaustive): "diagnose", "treat", "prescribe",
"administer", "dose", "medicate", "antibiotic", "therapy",
"withdrawal period".

## Why this line matters

Three concrete failure modes this boundary prevents:

1. **Regulatory exposure to the farmer.** A farmer who acts on
   an "administer X" cue without a vet prescription can face
   prosecution in the EU / US. The vendor of the cue engine
   can be pulled into the case as a proximate cause.
2. **Antimicrobial resistance.** Over-prescribed antibiotics
   in food animals drive AMR in humans. An automated "treat"
   recommendation that errs on the cautious side still
   accelerates that problem. Observation-only keeps the human
   vet in the loop.
3. **Welfare outcomes.** "Diagnose and treat" automations
   often miss the underlying welfare problem (inadequate
   bedding, ventilation, stocking density) in favour of a
   point-treatment. Keeping the referral human-in-the-loop
   forces a welfare-layer conversation.

## What gets reused from triage4

Conceptual, not literal. The DOMAIN_ADAPTATIONS.md index
estimates 50 % code reuse — all of it at the *pattern* level:

- Signature-scoring conventions (unit-interval, per-channel
  quality).
- Weighted-fusion of signature channels into an overall score.
- Grounded explanation pattern (never invent facts).
- Dataclass-level claims guard (different vocabulary).
- Test conventions (hypothesis-style, fixed seeds).
- `claims_lint` script adapted to the agtech vocabulary list.

## What does NOT get reused

- Larrey baseline, mortal-sign override, DARPA gate
  evaluators, `CasualtyNode`, `MedicHandoff` — all human-
  specific.
- triage4's `REGULATORY.md` / `SAFETY_CASE.md` /
  `RISK_REGISTER.md` — SaMD / IEC-62304 are human-medicine.
  triage4-farm would need its own regulatory set if it ever
  ships to regulated deployments (EU animal-welfare
  directive), but not medical-device regulation.

## When this line moves

If a future triage4-farm version starts recommending specific
antimicrobial protocols (even with vet sign-off), that crosses
into veterinary-decision-support territory. At that point the
right move is:

1. Fork **triage4-farm-vet** as a third sibling for
   vet-facing decision support.
2. Engage a regulatory consultant for the host jurisdiction
   (FDA CVM in US, EU CVMP).
3. Keep triage4-farm a pure farmer-facing observation tool.

Don't gradually erode the observation / veterinary-practice
boundary inside one codebase. Regulatory complexity compounds
badly when products blur their scope.

## In short

Same decision-support *infrastructure*. Different decision-
support *posture*. The farmer observes; the vet decides; the
system helps the farmer know when to call the vet.

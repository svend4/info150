# 08 — Veterinary clinic

Pre-visit pet health assessment via the pet owner's phone.
Reduce unnecessary clinic visits, triage emergency cases,
post-surgery recovery monitoring.

## 1. Use case

A pet owner uploads 30-60 seconds of phone video of their
dog or cat. The system detects abnormal gait, breathing
pattern, posture instability, pain behaviours (panting at
rest, reluctance to move a limb), estimates HR via
Eulerian if the pet is still enough, and generates a
pre-visit summary for the vet. The vet either schedules a
visit, recommends emergency care, or confirms it can wait.

## 2. Who pays

- Vet-clinic chains (VCA, BluePearl, IDEXX).
- Pet-insurance carriers (Trupanion, Petplan, Figo).
- Direct-to-consumer pet-health apps (VetSmart, Vetster,
  BondVet).
- Veterinary telemedicine services.

Revenue model: B2B SaaS per clinic + B2C subscription
($5-15/mo) + insurance rider ("reduces vet-visit copay by
X %").

## 3. What transfers from triage4

**~50 % reuse.**

- `FrameSource` — phone video upload.
- `signatures/posture_signature.py` — gait + instability.
- `signatures/breathing_signature.py` — respiratory rate
  (cats 20-30/min, dogs 10-30/min at rest, different bands
  from humans).
- `signatures/remote_vitals.py` — HR via Eulerian (higher
  cardiac frequencies: cats 140-220 bpm, dogs 60-140 bpm).
- `state_graph/conflict_resolver.py` — "limping because
  injured" vs "limping because nervous at vet" reconciliation.
- `triage_reasoning/uncertainty.py` — low-light, shaky-hand,
  partial-occlusion quality factors.
- `triage_reasoning/llm_grounding.py` — vet-facing grounded
  summary.
- `integrations/marker_codec.py` — offline handoff for rural
  large-animal vets.
- Dev infrastructure.

## 4. What has to be built

- **Quadruped skeletal topology** — similar to K3-1.3 wildlife
  work, but different per species (dog, cat, horse, cow,
  rabbit — 5 topologies to start).
- **Species classifier** — which animal is in the video.
  Trivially done with pretrained YOLO.
- **Pain-behaviour detector** — species-specific. Dogs:
  panting at rest, tucked tail, hunched posture. Cats: hiding,
  ear position, hunched abdomen. Horses: weight-shifting,
  flehmen grimace. Requires veterinary-literature-grounded
  rules per species.
- **Owner-facing mobile UX** — upload flow, not a dashboard.
  "Record your dog walking for 15 seconds".
- **Vet-facing dashboard** — similar IA to triage4 but with
  pet / owner / insurance metadata.

## 5. Regulatory complexity

**Low-medium.** Veterinary = no FDA SaMD framework. Some US
states regulate veterinary-telemedicine (not all allow it
without prior in-person visit). EU has Professional Veterinary
Code frameworks by country. Not human-PHI — pet-owner data is
standard consumer-privacy territory.

## 6. Data availability

**Low-medium.** Public veterinary video datasets are scarce.
Cornell Lab of Ornithology has some, Stanford has a dog-gait
corpus. Private data via clinic partnerships is the primary
route. IRB-equivalent (IACUC for animals) approval required
for any research protocol.

## 7. Commercial viability

**Medium-high.** Pet healthcare is a $35 B/y US market.
Insurance-backed ($3 B/y US pet insurance market) makes B2B
the stronger path. Telemedicine-for-pets is the fastest-
growing sub-segment. Competitors (Vetster, Kinship, TeleVet)
focus on video-call with vet — not on pre-visit automated
summary.

## 8. Engineer-weeks estimate

**12-16 weeks to MVP.** Weeks 1-4: copy-fork + dog topology
+ species classifier + recalibrate HR/RR bands. Weeks 5-10:
pain-behaviour rules for 3 species (dog, cat, horse). Weeks
11-14: owner mobile UX + vet dashboard. Weeks 15-16: one
clinic pilot.

## 9. Risk flags

- **Species under-coverage.** Covering only dogs + cats
  excludes ~30 % of vet practice (exotic, large animal,
  equine). Scope accordingly.
- **Owner-misuse risk.** Owner takes a video that hides the
  lame limb; system misses it; owner delays visit;
  preventable decline. Disclaimers + "if in doubt, visit"
  prompt are non-optional.
- **State-regulatory patchwork.** Texas vs California vs
  New York have very different telemedicine-for-pets rules.
  Legal audit per state before launch.
- **Veterinary adoption curve.** Vets are cautious about AI
  tooling — trust-building requires "grounded reasons"
  explanation, not black-box scores. The triage4 pattern is
  a genuine fit.

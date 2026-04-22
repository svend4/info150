# 10 — Livestock / agtech

Dairy / beef / poultry / swine farm herd-health monitoring.
Estrus detection, lameness, respiratory disease, heat stress.

## 1. Use case

Barn-mounted cameras + thermal sensors monitor animals
continuously. System tracks gait quality (lameness is the top
dairy-cattle welfare problem), respiratory rate (central for
early bovine respiratory disease), estrus behavioural
patterns (mounting, tail-flagging), feeding activity, and
thermal signatures of inflammation. Farmer gets daily health
reports + real-time alerts for urgent cases.

## 2. Who pays

- Dairy cooperatives (Arla, FrieslandCampina, Dairy Farmers
  of America).
- Integrated meat producers (Tyson, JBS, Smithfield).
- Farm-insurance carriers and banks lending against livestock.
- Dairy / beef-industry genetics companies (Genus, Semex).

Revenue model: per-animal-per-month SaaS ($1-5/head/mo
typical). Strong commercial pull — disease outbreaks cost
dairy farms $100-300 per sick cow in treatment + milk loss.

## 3. What transfers from triage4

**~50 % reuse.**

- `FrameSource` — barn CCTV / RTSP.
- `signatures/posture_signature.py` — lameness gait
  signature. Central.
- `signatures/breathing_signature.py` — respiratory rate,
  early bovine-respiratory-disease indicator.
- `signatures/thermal_signature.py` — localised inflammation
  (mastitis, hoof infection).
- `signatures/remote_vitals.py` — HR via Eulerian on short
  windows of stationary animals (much harder on moving).
- `state_graph/skeletal_graph.py` — quadruped topology
  (~18 joints), same as wildlife-terrestrial.
- `state_graph/conflict_resolver.py`.
- `triage_reasoning/uncertainty.py`.
- `autonomy/active_sensing.py` — which barn camera to
  prioritise given current herd activity.
- `world_replay/timeline_store.py` — per-animal history for
  vet review.
- Dev infrastructure.

## 4. What has to be built

- **Individual-animal identification** — ear-tag reader
  (visual OCR) or coat-pattern classifier. Commercial
  pretrained models exist for dairy Holsteins; harder for
  solid-colour beef breeds.
- **Lameness scorecard (DairyCo 1-5 scale)** — gait
  analysis producing a locomotion score. Published
  literature exists — this is the most studied
  aspect.
- **Estrus / heat detection** — mounting behaviour
  classifier (CNN on short clips).
- **Feeding-activity tracker** — time at feed bunk per
  animal, key welfare + productivity indicator.
- **Farmer-facing dashboard** — single-herd view,
  per-animal drill-down, vet-referral workflow.

## 5. Regulatory complexity

**Low.** No human-medical regulation. Animal-welfare
guidelines (EU Directive 98/58/EC) provide outcome targets
but no device regulation. Some jurisdictions (Netherlands,
Denmark) require automated welfare monitoring on large
farms — regulatory is an accelerator, not a blocker.

## 6. Data availability

**Medium-high.** Dairy industry funds research; several
open datasets exist (Cornell Dairy, University of Edinburgh
herd behaviour). Private partnerships yield plenty of labelled
video — farmers are co-operative because direct ROI.

## 7. Commercial viability

**High.** Agtech is well-funded ($7 B+ / yr VC). Dairy
monitoring has clear ROI (disease prevention, fertility
management). Several scaled competitors (Connecterra, Allflex
SenseHub, Smartbow, CowSignals) but market is large enough
for niche differentiation — e.g. explainability of decisions
(grounded triage4 pattern) vs their black-box scores.

## 8. Engineer-weeks estimate

**12-16 weeks to MVP.** Weeks 1-4: copy-fork + quadruped
topology + ear-tag reader. Weeks 5-10: lameness scorecard
(the hardest part — needs literature-validated calibration).
Weeks 11-14: farmer dashboard + vet referral. Weeks 15-16:
one-farm pilot.

## 9. Risk flags

- **Antibiotic-dosing recommendations.** Flagging "possibly
  sick" is fine; recommending "treat with tylosin" is
  veterinary-practice territory and illegal in most
  jurisdictions without a veterinary prescription. Handoff
  must be "call your vet", not "administer X".
- **Heat-stress false alarms.** Hot summer days in Texas
  make most cows look heat-stressed by some metric.
  Calibration must normalise for ambient environment via
  barn-sensor ingestion.
- **Feedlot vs pasture.** Camera coverage works in
  enclosed barns; extensive grazing operations (Australia,
  Argentina) are camera-impossible for most animals. Scope
  to intensive operations.
- **Milk-price volatility.** Farmer budgets swing with
  commodity prices; B2B contracts should include price-
  tiered pricing to survive downturns.

# 01 — Wildlife, terrestrial

Camera-trap networks, anti-poaching, endangered-species health
assessment, predator-movement tracking.

## 1. Use case

Fleet of camera traps + drones on a reserve. When something
moves in frame, the system classifies the animal, estimates its
health state (ambulatory / limping / collapsed), and flags
candidate threats (wire-snare injuries, emaciation, lactation
markers on females). An optional drone revisit is scheduled by
the same information-gain planner triage4 already ships.

## 2. Who pays

- Conservation NGOs (WWF, African Parks, Conservation X Labs).
- Government wildlife services (Kenya KWS, South Africa SANParks).
- EU Life-Nature research grants.
- Commercial safari operators who use animal-health data as
  a marketing / insurance hedge.

Revenue model: per-reserve licence + data-services subscription.
Not a consumer product. Sales cycle 6-12 months.

## 3. What transfers from triage4

**~60 % reuse.**

- `FrameSource` (any IP camera or SD-card replay).
- `signatures/thermal_signature.py` — hot-spot / asymmetry
  (wounds, infection).
- `signatures/posture_signature.py` — instability / collapse.
- `signatures/motion`, `remote_vitals.py` — movement quality,
  standoff HR from ordinary RGB on calm animals.
- `state_graph/skeletal_graph.py` — swap 13-joint humanoid for
  ~18-joint quadruped topology.
- `state_graph/conflict_resolver.py` — reconciles "injured vs
  just resting" hypotheses.
- `triage_reasoning/uncertainty.py`, `score_fusion.py`.
- `integrations/multi_platform.py` + bridges — multi-camera
  fleets + optional drone revisit.
- `autonomy/active_sensing.py` — which camera trap to revisit
  next.
- `world_replay/*` — timeline replay for ranger review.
- `marker_codec` — offline tag on a physical GPS collar.
- Dev infrastructure.

## 4. What has to be built

- **Species detector** — repurpose `LoopbackYOLODetector` with
  iNaturalist- / Snapshot-Serengeti-trained YOLO weights, or a
  MegaDetector wrapper.
- **Quadruped skeletal topology** — new joint set, new mirror
  pairs (front-left / front-right legs, back-left / back-right
  legs).
- **Species-specific red flags** — snare-induced limb deformity,
  tusk asymmetry on elephants, horn cracks on rhinos.
- **GPS-collar ingestion adapter** — Iridium / LoRa telemetry.
- **Ranger handoff** — SMS / satcom message templates instead
  of medic-payload JSON.

## 5. Regulatory complexity

**Low.** Wildlife observation has research-permit considerations
(CITES for listed species, local reserve IACUC-style protocols)
but no medical-device framework. The "no patient-like data"
rule from `RISK_REGISTER DATA-005` still applies — GPS
collar data is sensitive for anti-poaching reasons.

## 6. Data availability

**Medium.** Public datasets exist (iNaturalist, Snapshot
Serengeti, eMammal). Reserve-specific data usually requires a
partnership agreement. Rehabilitation-centre footage of injured
animals is the hardest to source and the most valuable for
calibration.

## 7. Commercial viability

**Medium.** Conservation NGOs have moderate budgets; SaaS ARR
per reserve ~$20-50k/y is realistic. Hardware partnerships with
camera-trap vendors (Reconyx, Bushnell, Browning) accelerate
integration.

## 8. Engineer-weeks estimate

**8-12 weeks to MVP** with public datasets + one partner reserve.
First 4 weeks: copy-fork triage4, swap topology, integrate
MegaDetector. Weeks 5-8: reserve deployment + calibration.
Weeks 9-12: ranger-facing UI + SMS handoff.

## 9. Risk flags

- **Anti-poaching data sensitivity.** GPS positions of protected
  animals are targets; the system must NEVER log unencrypted
  location data to anywhere an adversary can reach.
- **False-positive fatigue.** Rangers ignoring 100 "possible
  injury" alerts to find 1 real one defeats the system.
  Calibration must minimise FP rate over sensitivity.
- **Ecosystem over-reach.** Don't claim to "predict poaching
  events" or "optimise anti-poaching patrols" — that's a
  different project with different ethics.

# 03 — Wildlife, aquatic (fish / aquaculture)

Aquaculture (fish-farm health monitoring), wild-stock
assessment, marine-disease early warning.

## 1. Use case

Underwater cameras in salmon / trout pens continuously monitor
fish for signs of disease outbreak, parasite load (sea lice),
stress behaviour, and mortality. Gill-rate estimation via the
Eulerian pipeline replaces manual sampling. Schooling-behaviour
anomalies flag environmental stressors (oxygen drop,
algal bloom).

## 2. Who pays

- Aquaculture industry — salmon farms are the first market
  (Mowi, Cermaq, Leroy Seafood). A single farm can pay
  $50-200k/y for proven welfare monitoring.
- Marine research institutes (NOAA, WHOI, Hakai) for wild-stock
  applications.
- Fisheries ministries (Norway, Canada, Chile) that enforce
  animal-welfare audits.

Revenue model: per-pen sensor + SaaS subscription. Well-funded.

## 3. What transfers from triage4

**~45 % reuse.** Lower than terrestrial because underwater
visibility is fundamentally different.

- `FrameSource` (underwater camera, can be any RTSP).
- `signatures/remote_vitals.py` — gill-rate via Eulerian
  bandpass on the gill region. Validated pattern in
  aquaculture literature.
- `signatures/posture_signature.py` — fish-body axis
  instability.
- `state_graph/conflict_resolver.py`.
- `triage_reasoning/uncertainty.py` — water turbidity becomes
  a dominant uncertainty channel.
- `world_replay/*`.
- `autonomy/active_sensing.py` — next pen to inspect.
- Dev infrastructure.

## 4. What has to be built

- **Underwater computer vision** — visibility < 5 m, particle
  occlusion, blue-shift colour correction. Requires either
  white-light calibration or a pretrained underwater model
  (e.g. Fishial.ai, LSSS).
- **School-behaviour metric** — nearest-neighbour distance,
  polarization, inter-fish distance variance. Novel, not in
  triage4.
- **Sea-lice detector** — specific visual class. Commercial
  trained models exist (Umitron, ObservFood).
- **Fish skeletal topology** — minimal (head / body axis / tail),
  mostly for axis-instability detection not kinematics.
- **Mortality-event detector** — dead-fish-on-bottom
  classification, central for feed-conversion calculations.
- **Water-chemistry ingest** — DO, temperature, salinity from
  bundled pen sensors, fused with vision.

## 5. Regulatory complexity

**Low-medium.** EU aquaculture welfare regulations (Directive
98/58/EC) define outcome thresholds; some countries require
automated monitoring. Not medical-device-regulated. Minimal PHI
risk.

## 6. Data availability

**Medium.** Aquaculture datasets are mostly commercial (farmers
share with vendors who trained them on). Public: Fishial.ai,
FathomNet. Partnership with one farm to get labelled video from
a single pen is the realistic entry path.

## 7. Commercial viability

**High.** Salmon aquaculture is a $20 B/y industry where 10-20 %
of stock is lost to disease + parasites. Even a 5 % welfare
improvement is directly ROI-positive. Multiple funded startups
already operate here (Tidal AI, ScaleAQ, AquaCloud).

## 8. Engineer-weeks estimate

**14-18 weeks to MVP.** Longer than terrestrial because
underwater perception is harder. Weeks 1-4: copy-fork triage4,
integrate underwater image preprocessing. Weeks 5-10: gill-rate
+ sea-lice + school-behaviour metrics. Weeks 11-14: farm
partnership + calibration. Weeks 15-18: welfare-report
generation + KPI UI.

## 9. Risk flags

- **Crowded market.** Several incumbents with years of data
  already. Entry only makes sense with a differentiated angle
  (e.g. explicit decision-support explanations — their
  strength is black-box models).
- **Failure cost.** If the system misses a disease outbreak,
  the farm can lose $1M+ of stock in a week. Under-promise.
- **Environmental regulation.** Antibiotic-dosing decisions
  triggered by the monitoring output are subject to veterinary
  law in many jurisdictions. Do NOT directly recommend dosing —
  flag "consult a veterinarian" as the action.

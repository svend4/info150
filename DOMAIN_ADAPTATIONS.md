# Domain adaptations — triage4 beyond battlefield triage

Strategic map of civilian and non-human domains where the same
perception → signatures → reasoning → handoff pipeline could ship
as a sibling project in this monorepo. **Nothing here is a plan
or a commitment** — it's a structured brainstorm that frames how
much of `triage4/` is reusable vs. how much has to be written
from scratch for each candidate.

All conclusions are honest. No marketing tone. No product claims.

## 1. Monorepo philosophy

triage4 is decision-support for DARPA Triage Challenge–class
scenarios. Adapting it for a different domain splits cleanly
along three axes:

- **Domain-specific**: signatures that only make sense for the
  new subject (gill-rate for fish, wing-beat for birds, fatigue
  posture for athletes, etc.). ≈ 20–40 % of a new sibling's code.
- **Decision-support infrastructure**: `FrameSource`,
  `score_fusion`, `UncertaintyModel`, `PlatformBridge`,
  `MultiPlatformManager`, `TimelineStore`, `ForecastLayer`,
  `ConflictResolver`, `MarkerCodec`, `BayesianTwinFilter`,
  `MutMut` config, `ruff` / `mypy` / `claims-lint`,
  `hypothesis` scaffold, `Makefile`, `Dockerfile`, CI. ≈ 40–60 %
  of a new sibling's code. **This is the moat.**
- **Framing**: regulatory posture, risk register, language
  discipline. Every domain has its own framing — human
  pre-clinical is strictest, wildlife research is loosest,
  aquaculture is in between. ≈ 10–20 % per sibling.

## 2. What does NOT survive the jump

Before looking at what transfers, be explicit about what does not:

- `larrey_baseline.py` — Napoleonic human battlefield rules.
  Irrelevant for non-humans and irrelevant for non-triage
  decision surfaces (fitness, crowd safety).
- `MortalThresholds` — calibrated for human bleeding / chest
  motion / perfusion. Needs a from-scratch per-species or
  per-domain re-calibration.
- `CasualtyNode` fields `triage_priority`, `first_seen_ts`,
  `assigned_medic` etc. — semantics leak "casualty → medic"
  pipeline. Rename, re-type, but don't reuse as-is.
- DARPA Gate 1-4 + HMT evaluators — specific to the
  military-triage scoring.
- `docs/REGULATORY.md` — SaMD/IEC-62304 is human-medicine
  specific. Veterinary / agtech / wellness have separate
  frameworks.

## 3. The reusable core — what migrates nearly verbatim

- **`perception/frame_source.py`** — `LoopbackFrameSource`,
  `SyntheticFrameSource`, `build_opencv_frame_source`. Works on
  any RGB stream, any source (webcam, RTSP, recorded file,
  underwater camera, thermal camera feeding RGB-encoded frames).
- **`signatures/remote_vitals.py`** — Eulerian video
  magnification. Works on any vertebrate with a pulse visible
  in ordinary light. Just recalibrate the HR band.
- **`signatures/breathing_signature.py`** — chest-motion FFT.
  Works for any animal that breathes — mammals, birds (rapid
  breathing), reptiles. Re-tune bandpass per species.
- **`signatures/acoustic_signature.py`** — bandpower detector.
  Crucial for birds (calls), marine mammals (echolocation),
  livestock (distress), athletes (breathing rhythm).
- **`signatures/thermal_signature.py`** — hot-spot + asymmetry.
  Wound detection on wildlife, inflammation in livestock,
  exertion heat in athletes, engine-heat stress in drivers.
- **`signatures/posture_signature.py`** — asymmetry / collapse /
  instability. Transfers everywhere.
- **`state_graph/skeletal_graph.py`** — 13-joint humanoid by
  default. **Re-topology per subject**: ~18-joint quadruped,
  ~5-segment bird, ~10-segment fish. Framework is the same.
- **`state_graph/conflict_resolver.py`** — generic hypothesis
  reconciliation. Domain-agnostic.
- **`triage_reasoning/score_fusion.py`** — weighted fusion is
  trivially reusable; the mortal-sign override becomes a
  domain-specific "red flag" override with new thresholds.
- **`triage_reasoning/uncertainty.py`** — quality-weighted
  confidence. Generic.
- **`triage_reasoning/bayesian_twin.py`** — particle filter over
  any discrete state. Just re-define the state space.
- **`world_replay/*`** — generic timeline + replay.
- **`mission_coordination/*`** — generic task queue +
  assignment engine (when there's a notion of "tasks" and
  "executors").
- **`integrations/*`** — all platform bridges + multi-platform
  manager + bridge health + marker codec. Drones, quadrupeds,
  and ROS2 show up in wildlife, agtech, industrial safety,
  sports, and crowd monitoring unchanged.
- **Dev infrastructure** — `Makefile`, `Dockerfile`, CI workflow,
  mutmut, hypothesis, claims-lint (just re-author the forbidden
  word list), Prometheus metrics, SBOM generator. All generic.

## 4. Candidate sub-projects

14 domains worth considering. One per file under
[`docs/adaptations/`](docs/adaptations/), each with the same
9-section structure so they're easy to compare.

| # | Domain | File |
|---|---|---|
| 01 | Wildlife — terrestrial | [wildlife_terrestrial](docs/adaptations/01_wildlife_terrestrial.md) |
| 02 | Wildlife — avian (birds) | [wildlife_avian](docs/adaptations/02_wildlife_avian.md) |
| 03 | Wildlife — aquatic (fish / aquaculture) | [wildlife_aquatic](docs/adaptations/03_wildlife_aquatic.md) |
| 04 | Fitness / wellness | [fitness_wellness](docs/adaptations/04_fitness_wellness.md) |
| 05 | Telemedicine pre-screening | [telemedicine_pre_screening](docs/adaptations/05_telemedicine_pre_screening.md) |
| 06 | Elderly home monitoring | [elderly_home](docs/adaptations/06_elderly_home.md) |
| 07 | Industrial work safety | [industrial_safety](docs/adaptations/07_industrial_safety.md) |
| 08 | Veterinary clinic | [veterinary_clinic](docs/adaptations/08_veterinary_clinic.md) |
| 09 | Civilian disaster response | [disaster_response](docs/adaptations/09_disaster_response.md) |
| 10 | Livestock / agtech | [livestock_agtech](docs/adaptations/10_livestock_agtech.md) |
| 11 | Pool / beach safety | [pool_beach_safety](docs/adaptations/11_pool_beach_safety.md) |
| 12 | Sports performance | [sports_performance](docs/adaptations/12_sports_performance.md) |
| 13 | Driver monitoring | [driver_monitoring](docs/adaptations/13_driver_monitoring.md) |
| 14 | Crowd safety | [crowd_safety](docs/adaptations/14_crowd_safety.md) |

## 5. Scoring matrix

Each domain scored on 5 axes, integer 1-5, higher is better
(except regulatory complexity — inverted, 5 = easy, 1 = hard).

| # | Domain | Reuse % | Adaptation (eng-wk) | Regulatory | Data | Commercial |
|---|---|---|---|---|---|---|
| 01 | Wildlife — terrestrial | 60 | 8-12 | 5 | 3 | 3 |
| 02 | Wildlife — avian | 55 | 10-14 | 5 | 4 | 2 |
| 03 | Wildlife — aquatic | 45 | 14-18 | 4 | 3 | 4 |
| 04 | Fitness / wellness | **65** | **6-10** | **5** | **5** | **4** |
| 05 | Telemedicine pre-screening | **85** | 4-8 code + 12+ regulatory | 1 | 2 | 4 |
| 06 | Elderly home monitoring | 60 | 10-14 | 3 | 3 | 4 |
| 07 | Industrial work safety | 50 | 10-14 | 4 | 2 | 4 |
| 08 | Veterinary clinic | 50 | 12-16 | 4 | 3 | 3 |
| 09 | Civilian disaster response | **90** | **3-5** | 3 | 2 | 2 |
| 10 | Livestock / agtech | 50 | 12-16 | 5 | 4 | **4** |
| 11 | Pool / beach safety | 35 | 14-20 | 3 | 2 | 3 |
| 12 | Sports performance | 55 | 10-12 | 5 | 4 | 3 |
| 13 | Driver monitoring | 40 | 8-12 | 3 | 4 | 4 |
| 14 | Crowd safety | 55 | 10-14 | 4 | 2 | 3 |

## 6. Top-3 picks

Ranked by "highest commercial viability that can be tackled with
existing resources in the shortest time":

### 🥇 **Fitness / wellness** (04)

- 65 % code reuse, 6-10 weeks to MVP.
- **Low regulatory** burden (general wellness, not SaMD).
- Data comes from any webcam + gym-partnership agreements.
- Clear customer base (gyms, home fitness apps).

### 🥈 **Livestock / agtech** (10)

- 50 % reuse, 12-16 weeks.
- Agtech sector is commercially funded.
- Data access via farmer-partnership agreements is
  straightforward.
- No human-medicine regulatory overhead.

### 🥉 **Civilian disaster response** (09)

- 90 % reuse, 3-5 weeks (mostly vocabulary + partner
  integration).
- Natural adjacency to triage4's existing posture.
- NGO-fundable rather than commercial, but grant-aligned.
- Low revenue but high visibility.

### Runners-up

- **Telemedicine pre-screening (05)** — highest reuse (85 %)
  but the regulatory cost alone makes it a 6-12 month effort,
  not a 2-month pivot. Park until a clinical partner appears.
- **Elderly home monitoring (06)** — strong long-term market
  but needs a product partner (insurance, senior-living chain).

## 7. Proposed monorepo layout

**Critical:** do NOT prematurely extract a `biocore/` package.
Monorepos get worse, not better, when the first sibling forces
a shared-core abstraction before the second and third siblings
prove what "shared" means.

Correct sequence:

```
info150/
├── triage4/                # the flagship
├── triage4-fit/            # 2nd sibling — just copy-fork triage4/
├── triage4-vet/            # 3rd sibling — copy-fork again
└── biocore/                # extracted only AFTER ≥ 3 siblings converge
                            # on identical API surfaces (year 2+)
```

Each sibling project:

- lives in its own directory at the monorepo root
- has its own `pyproject.toml`, `Makefile`, CI workflow,
  `docs/`, `tests/`
- starts by copy-forking `triage4/` wholesale, then renames
  `CasualtyNode` → domain-specific, trims / rewrites what
  doesn't apply, adds domain-specific signatures
- keeps its own regulatory framing (`REGULATORY.md`,
  `RISK_REGISTER.md`) because every domain has different rules

## 8. Anti-patterns to avoid

- **Premature abstraction.** Writing `biocore/` before the
  second sibling forces its own conventions on the first one.
  Fix: copy-fork, don't abstract.
- **Regulatory cross-contamination.** Running fitness code and
  clinical code in the same process risks "medical-adjacent
  product" framing. Fix: hard package boundary, separate
  CI pipelines, separate Dockerfile, separate deployment.
- **Shared state graph.** A `MissionGraph` with both human
  patients and farm animals in it produces nonsense KPIs. Fix:
  one mission graph per deployment.
- **Cross-domain data leakage.** A calibration dataset trained
  for humans should never be fed through a fitness sibling
  without relabelling. Fix: per-sibling datasets, separate
  S3 buckets or local directories, explicit "sibling X was
  trained on dataset Y" provenance in the README.
- **Feature creep into the flagship.** Every wildlife feature
  that "could also apply to triage4" is a trap that pollutes
  the decision-support posture. Fix: new features land in the
  sibling first, and only migrate upstream when triage4 has
  a concrete use case.
- **Over-generalisation in the name of DRY.** Three similar
  lines of code is not a reason for an abstraction. Wait for
  five or seven.

## 9. Integrity note

This document is pure strategy analysis. Nothing here is a
commitment, a product claim, or a schedule. None of the 14
candidate siblings has been started. No customer, grant,
partner, or clinical / research protocol has been engaged for
any of them. The numbers in section 5 are **my best estimates
given the current state of triage4**, not empirical
measurements — they should be treated as an order-of-magnitude
guide, not a quote.

See [`ARCHIVES.md`](ARCHIVES.md) for provenance of the original
conversation that seeded triage4, and
[`triage4/docs/STATUS.md`](triage4/docs/STATUS.md) for the
current technical + conceptual state of the flagship.

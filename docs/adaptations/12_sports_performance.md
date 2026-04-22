# 12 — Sports performance

Professional + semi-pro team analysis. Injury prediction,
technique optimisation, fatigue tracking. Unlike fitness
wellness, this is **performance** not general consumer.

## 1. Use case

Fixed cameras in a training facility + wearable sensors
monitor athletes during training sessions and matches.
System identifies injury-precursor patterns (asymmetric
gait, favouring one side, decreased ROM), tracks fatigue
accumulation across sessions, provides form analysis on
sport-specific movements (a pitcher's throwing motion, a
tennis player's serve, a sprinter's stride). Output goes
to coaches + athletic trainers + sports physicians.

## 2. Who pays

- Professional teams (NFL, Premier League, NBA).
- College / national-team athletics programmes.
- Sports-medicine clinics + orthopaedic practices.
- Equipment manufacturers (Nike, Adidas) for product-
  development R&D.
- Tier-2 professional leagues + elite youth academies.

Revenue model: high-ticket B2B ($50-200k/yr per team),
crowded market.

## 3. What transfers from triage4

**~55 % reuse.**

- `FrameSource` — facility cameras.
- `signatures/posture_signature.py` — form analysis +
  asymmetry. Core.
- `signatures/motion` — stride / swing mechanics.
- `signatures/breathing_signature.py` — recovery rate
  between intervals.
- `signatures/remote_vitals.py` — resting + post-session
  HR via Eulerian.
- `state_graph/skeletal_graph.py` — humanoid topology
  unchanged.
- `state_graph/conflict_resolver.py` — "gait change because
  injured vs because fatigued".
- `triage_reasoning/uncertainty.py`.
- `triage_reasoning/bayesian_twin.py` — pattern reused:
  particle filter over (injury-risk-band, fatigue-band) per
  athlete.
- `triage_reasoning/llm_grounding.py` — grounded coach
  reports.
- `world_replay/*` — session replay for coaching.
- `world_replay/forecast_layer.py` — injury-risk projection.
- Dev infrastructure.

## 4. What has to be built

- **Sport-specific movement classifiers** — throwing, batting,
  kicking, jumping, etc. Per sport, per position.
- **Wearable-sensor fusion** — Catapult / WIMU / StatSports
  GPS vests are standard; ingest their data alongside
  vision.
- **Injury-risk model** — temporal-CNN on pose + workload
  data. Requires labelled historical injury data from a
  partner team — not a publicly available dataset.
- **Per-athlete baseline learner** — each athlete's "normal"
  form baseline learned across weeks.
- **Coach + trainer + physician dashboards** — three
  different audiences with three different IAs.

## 5. Regulatory complexity

**Low.** No medical-device framework for sports performance.
Some jurisdictions (EU, Canada) require athlete data-rights
agreements (similar to GDPR Article 9 for health data when
the athlete is a minor or vulnerable). Clinical-use claims
("prevents injury") cross into medical — stick to "flags
precursor patterns for trainer review".

## 6. Data availability

**Medium.** MoCap libraries (CMU, HDM05, KIT), SportVU
basketball data, public broadcast footage. Injury-labelled
data is proprietary and partner-gated. Academies are often
willing partners for research.

## 7. Commercial viability

**Medium-high.** Sports analytics is $3 B+ / yr and growing.
Crowded market: Catapult, Kinexon, Zone7 (injury), Pixellot
(vision), Hudl. Differentiation requires either a new sport
(Olympic niche sports are under-served), or grounded-
explanation differentiator against the black-box
incumbents.

## 8. Engineer-weeks estimate

**10-12 weeks to MVP for one sport.** Weeks 1-3: copy-fork
triage4 + sport-movement classifier for one vertical (e.g.
soccer). Weeks 4-7: injury-risk model + per-athlete baseline.
Weeks 8-10: coach + physician dashboards. Weeks 11-12:
academy pilot.

## 9. Risk flags

- **Crowded incumbent market.** Catapult has 15+ years of
  data across every major league. Entry must have a sharp
  angle (grounded explanations, a specific sport niche,
  price disruption).
- **Injury-prediction overclaim.** "Predicts injury" is a
  marketing trap — models at best flag increased risk.
  Language must be precise.
- **Athlete-data sensitivity.** Leaked injury status can
  cost athletes contracts. Infrastructure must be
  secure (encryption, access control, audit logs).
- **League politics.** Major leagues (NFL, NBA) have strict
  data-ownership rules — clubs may not be able to share
  their tracking data with outside vendors freely.
  Check league CBAs per partner.

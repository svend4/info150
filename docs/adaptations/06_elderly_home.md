# 06 — Elderly home monitoring

Fall detection, daily-activity monitoring, subtle-decline
early-warning. Stand-off camera in the home, no wearable
required.

## 1. Use case

Stationary cameras in common rooms (living room, bathroom
entrance, bedroom) provide passive monitoring of an elderly
person living alone or with minimal supervision. The system
detects falls, tracks activities-of-daily-living (ADL)
patterns, flags unusual deviations (hasn't left the bedroom
by 10 AM for the third day), and summarises weekly trends
for family / caregivers.

## 2. Who pays

- Senior-living chains (Sunrise Senior Living, Brookdale).
- Aging-in-place insurers / Medicare Advantage plans who
  benefit from delayed transitions to skilled-nursing care.
- Adult children of aging parents (direct-to-consumer, B2C).
- NHS / social-services pilot programmes in UK, Germany,
  Netherlands, Japan.

Revenue model: B2B SaaS per resident + B2C subscription
($30-80/mo).

## 3. What transfers from triage4

**~60 % reuse.**

- `FrameSource` — any home IP camera.
- `signatures/posture_signature.py` — core fall-detection
  signal.
- `signatures/breathing_signature.py` — detects motion while
  sleeping, sleep quality surrogate.
- `signatures/remote_vitals.py` — resting HR trends via
  Eulerian when subject is still.
- `state_graph/conflict_resolver.py` — "fall vs bent down to
  pick something up" reconciliation.
- `triage_reasoning/uncertainty.py` — low-light confidence
  adjustment.
- `triage_reasoning/llm_grounding.py` — weekly-summary
  natural-language report for family.
- `world_replay/timeline_store.py` + forecast layer — ADL
  timeline, weekly trend projection.
- `integrations/marker_codec.py` — offline alert dispatch
  via SMS/email gateway when internet is down.
- Dev infrastructure.

## 4. What has to be built

- **Activities-of-daily-living (ADL) classifier** — new:
  sitting, standing, walking, eating, toileting (without
  camera in bathroom — door transitions only), sleeping.
  CNN on keypoint sequences.
- **Fall-vs-non-fall classifier** — temporal-CNN on pose
  trajectory. Critical for product viability.
- **Routine-deviation detector** — per-resident baseline
  learned over 2-3 weeks, alerts on statistical anomaly.
- **Family-facing app** — weekly summary, emergency alerts,
  privacy controls (blur bathrooms / bedrooms per consent).
- **Privacy-first architecture** — on-device inference only,
  raw video never leaves the home. Only structured events
  uploaded.

## 5. Regulatory complexity

**Medium.** Falls between wellness and medical. In the US,
FDA Class I medical device or "consumer health" depending on
exact claims. "Alerts family of potential fall" — Class II.
EU — similar bifurcation. HIPAA applies if data goes through
a healthcare operator. GDPR applies for EU residents by
default.

## 6. Data availability

**Medium.** TUG (Timed Up and Go), UCF-101 elderly-activity
subset, Kinetics-600 subset exist but are not
elderly-home-specific. The best data comes from
home-deployment pilots with informed consent. IRB approval
required for research protocols.

## 7. Commercial viability

**High, growing.** Aging population is the largest demographic
force in developed economies. Medicare Advantage plans
explicitly value fall-prevention tooling (CPT codes exist for
fall-risk assessment). Three large commercial competitors
(SafelyYou, CarePredict, Rest Digital) — differentiation
needed.

## 8. Engineer-weeks estimate

**10-14 weeks to MVP.** Weeks 1-4: copy-fork triage4 + fall
classifier. Weeks 5-8: ADL classifier + routine-deviation
detector. Weeks 9-12: family-facing mobile app + privacy
controls. Weeks 13-14: home-pilot calibration (5-10 volunteer
households).

## 9. Risk flags

- **False-positive fatigue.** Every false fall alert trains
  family to ignore the system. Calibration must target
  99 %+ precision at the cost of some recall.
- **False-negative liability.** Missing a real fall where
  the elder lies on the floor for hours is the product's
  worst failure mode. Secondary signal (no motion for
  2+ hrs) should run in parallel as a backstop.
- **Privacy fundamentalism required.** On-device processing,
  no cloud, bathroom-blurring, per-room opt-outs — all
  non-optional. "Cameras watching grandma" is a marketing
  disaster without aggressive privacy framing.
- **Camera placement ambiguity.** Bedroom camera is contested
  — family wants fall detection, elder wants privacy. Config
  must expose this as a per-room consent toggle with clear
  trade-off copy.

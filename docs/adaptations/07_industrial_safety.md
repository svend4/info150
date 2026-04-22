# 07 — Industrial work safety

Construction sites, mines, offshore rigs, warehouses. Detect
exhaustion, fall risk, heat stress, PPE compliance, unsafe
posture during lifting.

## 1. Use case

Fixed cameras + wearable thermal sensors monitor workers on
a site. System flags: (a) PPE non-compliance (missing hard
hat, vest, harness); (b) unsafe lifting posture; (c) fatigue
indicators (slowed gait, postural drift); (d) heat-stress
signatures (flushed skin, slowed movement + high ambient
temp); (e) falls or near-misses. Alerts go to site safety
officer, not to the worker directly.

## 2. Who pays

- Construction firms (Skanska, Bechtel, Turner).
- Mining multinationals (BHP, Rio Tinto, Vale).
- Oil / gas operators (Shell, BP, Chevron).
- Insurance carriers (AIG, Zurich, AXA) — for premium
  discounts.
- OSHA / HSE-regulated sectors generally.

Revenue model: per-site SaaS license + insurance-coupled
premium reduction.

## 3. What transfers from triage4

**~50 % reuse.**

- `FrameSource` — site CCTV / RTSP.
- `signatures/posture_signature.py` — core unsafe-lifting
  detector.
- `signatures/thermal_signature.py` — heat-stress signature.
- `signatures/motion` — fatigue gait analysis.
- `state_graph/conflict_resolver.py`.
- `triage_reasoning/uncertainty.py` — site-conditions
  (dust, rain) affect confidence.
- `autonomy/active_sensing.py` — which camera to prioritise
  based on activity zone + risk.
- `integrations/multi_platform.py` — multi-camera fleet.
- `world_replay/*` — incident replay for root-cause
  analysis.
- Dev infrastructure.

## 4. What has to be built

- **PPE detector** — hard hat, vest, safety glasses, harness.
  YOLO-family, multiple pretrained options (Viso.ai,
  Safety-AI).
- **Zone-access classifier** — which worker in which
  restricted zone (requires RFID badge integration or
  face-recognition — second is privacy-hot).
- **Slip-trip-fall pattern detector** — distinct from
  elderly-home fall: running worker on uneven surface.
- **Near-miss detector** — intersect tool paths with
  worker trajectory in 3D.
- **Site-ops dashboard** — totally different IA from
  triage4's. Event feed, heat-map of risk zones per hour,
  crew-level KPIs.
- **Alert-dispatch integration** — SMS to safety officer
  + radio tone, not just dashboard.

## 5. Regulatory complexity

**Low-medium.** OSHA / HSE context — not medical-device
regulation. GDPR applies when EU workers are monitored;
some jurisdictions (France, Germany) have strict workplace-
surveillance laws requiring union consent and strict
data-retention limits. Not SaMD.

## 6. Data availability

**Low.** Most worker-video is proprietary, NDA-locked.
Public: COCO subset, OpenImages, SafetyAI industry dataset.
Real calibration requires a site-pilot partnership — and
many sites refuse cameras-on-workers for workforce-relations
reasons.

## 7. Commercial viability

**High.** Fatalities on construction sites are well-tracked
and costly — US OSHA reports 1008 construction-fatalities in
2022. Insurance discounts of 10-20 % for sites using
monitoring are common. Market is growing but fragmented (many
vendors, none dominant yet — Voxel, Smartvid.io, INX+, etc.).

## 8. Engineer-weeks estimate

**10-14 weeks to MVP.** Weeks 1-4: copy-fork + PPE detector
integration. Weeks 5-8: fatigue / heat-stress / fall
detectors. Weeks 9-12: site-ops dashboard + alert dispatch.
Weeks 13-14: site pilot + calibration.

## 9. Risk flags

- **Workforce surveillance.** Workers view this as
  employer-spying. Union-consent process + strict
  data-retention limits (≤ 30 days, no individual
  performance metrics) is a product-survival issue.
- **Liability shift.** If the site installs the system and
  a worker gets hurt, insurance may claim the system "should
  have" detected the hazard. Contract language must limit
  to "decision-support, not replacement for safety
  officer".
- **Face-recognition regulation.** GDPR + US state laws
  (BIPA in Illinois) sharply limit biometric matching.
  Default to RFID-badge ID over face-ID.
- **Alert-fatigue.** 100 PPE-violation alerts an hour is
  unusable. Calibrate per site, aggregate to "hot zones"
  rather than per-worker events.

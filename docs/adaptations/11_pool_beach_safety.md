# 11 — Pool / beach safety

Drowning detection for public pools, hotel pools, beaches,
water parks. Real-time alerts to lifeguards.

## 1. Use case

Cameras above (and ideally below) a pool or swim beach watch
for drowning signatures: instinctive drowning response (IDR —
head low in water, vertical body posture, non-rhythmic
splashing), silent submersion (most drownings), absent
swimmer (swimmer entered but hasn't surfaced in N seconds).
Alert goes to lifeguard pendant / watch.

## 2. Who pays

- Public-pool operators (municipalities, YMCAs).
- Hotel chains (Marriott, Hilton, Four Seasons).
- Cruise lines (pool deck monitoring on massive ships).
- Water-park operators (Six Flags, Disney, Universal).
- Beach municipalities for guarded swim zones.

Revenue model: per-pool SaaS subscription + one-time hardware
install. Liability-insurance-driven pricing.

## 3. What transfers from triage4

**~35 % reuse — the lowest practical of the 14.** Underwater
is very different from triage4's visible-light stand-off
model.

- `FrameSource` — above-water camera. Underwater requires a
  wholly new preprocessing pipeline.
- `signatures/posture_signature.py` — IDR posture (vertical
  in water, head low).
- `signatures/motion` — submersion duration tracker.
- `state_graph/conflict_resolver.py` — "drowning vs kid
  playing dead vs diving for toy" reconciliation.
- `triage_reasoning/uncertainty.py` — water turbidity,
  surface-sun-glare quality factors.
- `autonomy/active_sensing.py` — which zone the lifeguard
  should scan next.
- `integrations/multi_platform.py` — camera fleet.
- `world_replay/*` — incident replay.
- Dev infrastructure.

## 4. What has to be built

- **Swimmer detection underwater** — requires new model.
  Public datasets are very limited. Commercial competitors
  (Poseidon Swim, AngelEye, Coral Detection) hold most
  training data.
- **IDR classifier** — temporal classifier on above-water
  posture. IDR has a distinct visual signature but very
  brief window (20-60 s).
- **Absent-swimmer tracker** — swimmer enters zone, doesn't
  exit within expected time, isn't visible. Requires
  person re-identification across cameras.
- **Underwater camera integration** — submersion, pressure
  housing, IR vs visible. Hardware layer not trivial.
- **Lifeguard-wearable alert** — pendant / smartwatch
  integration with vibration + audio tone, not just a
  dashboard.

## 5. Regulatory complexity

**Medium.** Life-safety product. Class I medical device in
some jurisdictions if claims include "saves lives". Liability
law (tort) is the dominant concern — a missed drowning is a
wrongful-death lawsuit. E+O insurance mandatory + $10M+
coverage typical.

## 6. Data availability

**Low.** Ethics + liability prevent public drowning-video
datasets from existing. Training relies on simulated
drowning (actors holding IDR poses), retrospective analysis
of real incidents (limited access), and commercial
incumbents' proprietary sets.

## 7. Commercial viability

**Medium.** 4000 drowning deaths / year in the US alone make
this a real safety problem, but the market is crowded with
3-4 incumbents (Poseidon, AngelEye, SwimEye) that have 10+
years of deployment data. Entry requires either very clear
differentiation (e.g. better explainability of alerts) or a
lower-cost open-hardware offering.

## 8. Engineer-weeks estimate

**14-20 weeks to MVP.** Weeks 1-6: underwater perception
pipeline from scratch. Weeks 7-12: IDR + absent-swimmer
classifiers. Weeks 13-16: lifeguard-wearable integration.
Weeks 17-20: one-pool pilot + calibration against
instructor-labelled events.

## 9. Risk flags

- **Wrongful-death exposure.** A missed drowning with this
  product installed invites a lawsuit alleging
  false-reassurance. Contracts must be very clear: the
  system supports lifeguards, does not replace them.
- **Lifeguard replacement temptation.** Hotel GMs will try
  to use the product to reduce lifeguard headcount. That
  undermines safety AND invalidates insurance. Deployment
  contracts should forbid lifeguard-ratio reductions as
  a consequence of installation.
- **Privacy backlash.** Cameras in bathing-suit contexts —
  particularly with children — are a PR minefield. On-device
  processing, no upload of raw video, and clear posted
  signage are product requirements.
- **Hardware complexity.** Unlike the other 13 candidates,
  this one requires waterproof camera enclosures, tamper-
  proof mounting, and network reliability in a humid
  chlorinated environment. Hardware vendor lock-in is
  likely.

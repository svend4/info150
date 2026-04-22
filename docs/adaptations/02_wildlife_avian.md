# 02 — Wildlife, avian (birds)

Migration tracking, nest monitoring, avian-flu early warning,
injured-bird rescue triage. Acoustic-heavy domain.

## 1. Use case

Passive acoustic monitoring on a bird reserve or migration
corridor identifies species from calls, flags distress / injury
vocalisations, cross-references with optical + thermal to
differentiate a sick bird from a healthy one behaving oddly.
Dead-bird-on-ground detection (visual) triggers avian-flu
surveillance sampling workflows.

## 2. Who pays

- Ornithology research institutes (Cornell Lab of Ornithology,
  British Trust for Ornithology).
- National disease surveillance agencies (USDA APHIS, EFSA)
  for avian-flu outbreaks.
- Nature reserves + migration hubs (Sempach Switzerland, Point
  Pelee Canada).

Revenue model: research-grant-funded tooling + government
contracts during disease-outbreak windows.

## 3. What transfers from triage4

**~55 % reuse.**

- `signatures/acoustic_signature.py` — central, becomes the
  primary sensor. Bandpower detectors for target species calls
  + distress categories.
- `signatures/remote_vitals.py` — wing-beat frequency as a
  stand-off HR proxy on video of perched / slow-flying birds.
- `signatures/thermal_signature.py` — body-temp anomalies
  (avian-flu birds often run febrile before visible symptoms).
- `FrameSource` — any reserve camera.
- `state_graph/conflict_resolver.py` — reconciles "injured vs
  territorial-display" hypotheses.
- `triage_reasoning/uncertainty.py`.
- `autonomy/active_sensing.py` — which nest / station to
  revisit.
- Dev infrastructure.

## 4. What has to be built

- **Species classifier from calls** — BirdNET / perch weights
  or a custom model. Public models exist; integration is
  straightforward.
- **Avian skeletal topology** — simpler than quadruped (head,
  body, two wings, two legs, tail — ~7 segments). Used for
  visual health detection, not kinematics.
- **Migration-path tracker** — multiple-observation-point
  aggregation, leaves triage4's single-mission assumption.
- **Dead-bird-on-ground detector** — new visual class, critical
  for avian-flu surveillance.
- **Ringing / banding database adapter** — link observations to
  ringed individuals when leg-band visible.

## 5. Regulatory complexity

**Low.** Research-permit regulation only. No medical-device
framework.

## 6. Data availability

**Medium-high.** xeno-canto has 800k+ recorded bird calls under
CC licence. Cornell Macaulay Library adds millions more.
Visual: eBird photos, iNaturalist. Avian-flu-specific training
data is scarcer — typically a research partnership with a
national surveillance lab.

## 7. Commercial viability

**Low-medium.** Mostly academic / government grant funded. No
consumer play. One-off commercial licensing to film production
(wildlife documentaries) is an adjacent niche.

## 8. Engineer-weeks estimate

**10-14 weeks to MVP.** Acoustic-first perception is a
significant shift — 4-6 weeks to integrate BirdNET and wire
call-classification confidence into the existing uncertainty
model. Visual health detection + dead-bird-on-ground is another
4 weeks. Field deployment + calibration at one reserve is
2-4 weeks on top.

## 9. Risk flags

- **Model-training cost.** Species classifiers need retraining
  per geography. Public models cover major regions but
  underperform in less-sampled ones (Amazon, Borneo).
- **Audio privacy.** Passive acoustic monitoring in populated
  areas picks up human conversations. Calibration must
  explicitly mute / discard voice frequencies.
- **Overclaim risk.** "Detects avian flu" is not a clinical
  claim the system can make — it flags candidate mortality
  events for human-led sampling. Language in the handoff
  payload must reflect this strictly.

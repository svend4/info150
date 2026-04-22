# 14 — Crowd safety

Stadiums, music festivals, transit hubs, religious
gatherings. Detect medical emergencies in crowds — fainting,
seizures, falls, and crowd-density / crowd-crush precursors.

## 1. Use case

Fixed overhead + side cameras cover venue + perimeter.
System flags individual medical events (someone collapses in
a seated crowd, seizure-pattern movement, motionless person
after a stampede), tracks crowd density against
safe-threshold maps, detects crush-precursor patterns
(pressure waves, uni-directional flow into a choke point).
Alerts go to venue medical + security teams.

## 2. Who pays

- Large-venue operators (AEG, Live Nation, Madison Square
  Garden).
- Stadium owners (NFL, Premier League, UEFA).
- Transit-authority operators (London Underground, NYC MTA,
  Paris RATP).
- Religious-event organisers (Hajj authorities in Saudi
  Arabia, Kumbh Mela in India).
- Event insurance carriers (Allianz, Lloyd's).

Revenue model: per-event or per-venue SaaS. Insurance-
premium coupled pricing.

## 3. What transfers from triage4

**~55 % reuse.**

- `FrameSource` — venue CCTV.
- `signatures/posture_signature.py` — collapsed-person
  detection.
- `signatures/motion` — unusual motion patterns (seizure
  kinematics).
- `state_graph/conflict_resolver.py` — "collapsed vs sitting
  on the ground" reconciliation.
- `triage_reasoning/uncertainty.py`.
- `autonomy/active_sensing.py` — which camera to cue the
  operator to inspect.
- `integrations/multi_platform.py`.
- `world_replay/*` — incident replay for post-event
  forensics.
- Dev infrastructure.

## 4. What has to be built

- **Person detector + tracker** — standard (ByteTrack +
  YOLOv8-pose).
- **Density-map generator** — flow field + density heat-map
  over the venue. Novel for triage4. Based on published
  crowd-safety literature (Helbing et al.).
- **Crush-precursor detector** — detects pressure-wave
  propagation through a crowd. Very domain-specific.
- **Collapsed-person in crowd** — requires seeing the
  person AT ALL (occluded if crowd packs around them).
  Thermal camera augmentation helps.
- **Venue-safety dashboard** — heat-map view, density
  gauge, incident feed. Distinct from all other siblings.
- **Security-team alert flow** — pendants, radios, in-
  venue PA integration.

## 5. Regulatory complexity

**Low-medium.** Public-safety product — no medical-device
framework. Privacy: large-scale face recognition at events
is legally contested (EU AI Act restricts it in public
spaces; US state laws vary). Default to
pose-only, no face-recognition. GDPR applies for EU events.

## 6. Data availability

**Low.** Crowd-crush events have limited forensic video
(Hillsborough 1989, Love Parade 2010, Itaewon 2022 are the
studied cases). Synthetic-crowd simulators (PED-SIM, JuPedSim)
exist for training density models. Real deployments
constitute the calibration set.

## 7. Commercial viability

**Medium.** Mega-events are willing to pay for safety
(Hajj organisers reportedly spend $100M+ on crowd-
management tech). Smaller venues are price-sensitive.
Crowded field — VisionLabs, Agent Vi, Briefcam — but most
compete on security (knife detection, perimeter breach)
not medical + crowd-flow combined.

## 8. Engineer-weeks estimate

**10-14 weeks to MVP.** Weeks 1-3: copy-fork + person
tracker. Weeks 4-7: density map + crush-precursor detector
(hardest part, needs simulator training). Weeks 8-11:
venue dashboard + alert flow. Weeks 12-14: pilot at a
mid-size venue.

## 9. Risk flags

- **Face-recognition conflation.** Venues will want
  face-rec "while you're at it". Refusing cleanly is a
  product-positioning requirement — accepting it turns the
  product into surveillance tech and invites AI-Act /
  biometric-law problems.
- **False-positive crush alerts.** A stadium at 90 %
  capacity looks crushed by some density metrics.
  Calibration per venue, per event type, per weather is
  a heavy ongoing load.
- **Insurance dependency.** Revenue depends on insurance
  carriers accepting the product as risk-reducing. That
  means actuarial validation — years of data before
  premium discounts are approved.
- **Public-safety liability.** Missing a crush event with
  the system installed is wrongful-death exposure on mass
  scale. E+O insurance minimum $50M; contracts must be
  tight on "decision-support vs replacement".
- **Mega-event access is pay-to-play.** Hajj, World Cup,
  Olympics contracts are decided years in advance with
  incumbent preferred vendors.

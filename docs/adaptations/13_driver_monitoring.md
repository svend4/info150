# 13 — Driver monitoring

In-cab camera watches the driver for drowsiness, distraction,
medical emergency (sudden incapacitation). Fleet vehicles,
long-haul trucks, insurance telematics.

## 1. Use case

Camera mounted above the dashboard continuously monitors
the driver's face + upper body. System detects: (a)
drowsiness signatures (eye closure, head nod, yawn); (b)
distraction (phone use, looking away > N seconds); (c)
medical emergency (sudden slumping, loss of postural tone,
arrhythmia via Eulerian if face-pulse is clear enough); (d)
heat / carbon-monoxide hazard via thermal and ambient
sensors. Alerts escalate from in-cab tone → fleet dispatcher
→ emergency services.

## 2. Who pays

- Fleet operators (UPS, Schneider, Ryder, Amazon Logistics).
- Long-haul trucking (J.B. Hunt, XPO, Werner).
- Ride-share platforms (Uber, Lyft).
- Car-insurance telematics (Progressive Snapshot, Tesla).
- OEM driver-assistance programmes.

Revenue model: per-vehicle SaaS subscription + insurance
premium reduction. Clear ROI when tied to insurance discount.

## 3. What transfers from triage4

**~40 % reuse — lower than most, because driver monitoring
is dominated by face / eye dynamics that aren't central in
triage4.**

- `FrameSource` — in-cab camera.
- `signatures/remote_vitals.py` — Eulerian HR from face for
  arrhythmia / incapacitation detection.
- `signatures/posture_signature.py` — slumping, head-tilt.
- `signatures/thermal_signature.py` — heat / CO exposure.
- `state_graph/conflict_resolver.py` — "looking away because
  checking mirror vs distracted".
- `triage_reasoning/uncertainty.py`.
- `triage_reasoning/bayesian_twin.py` — drowsiness-band
  particle filter.
- `world_replay/*` — incident replay for dispatcher.
- Dev infrastructure.

## 4. What has to be built

- **Face + eye tracker** — MediaPipe Face Mesh is the
  baseline. Drowsiness models use PERCLOS (percentage of
  eyelid closure) + microsleep detection.
- **Gaze tracker** — where the driver is looking (road /
  mirror / phone / passenger). Distraction detection.
- **Smoke / yawn detector** — both have telltale visual
  signatures.
- **Emergency-escalation flow** — dispatcher-in-the-loop,
  optional automatic 112 / 911 call on incapacitation.
- **OEM integration** — CAN-bus access for speed /
  steering-angle / lane-departure cross-correlation.
- **Per-driver baseline** — some drivers naturally
  head-nod; baseline learned in first 50 hrs of driving.

## 5. Regulatory complexity

**Medium.** EU MDR (when marketed for health features) +
UNECE R79 (lane-keeping + driver-monitoring regulation) +
GDPR (in-cab camera is highly privacy-sensitive) +
US-state biometric laws (BIPA Illinois, Texas CUBI).
Tesla / Mobileye precedent shows it's navigable but not
trivial.

## 6. Data availability

**Medium.** DMD (Drowsiness Monitoring Dataset), DROZY,
YawDD — several public datasets. Real-world fleet data via
partnership. Accident-data for validation is hard — fatal
fatigue crashes are rare per-fleet but common in aggregate.

## 7. Commercial viability

**High.** Global fleet-monitoring market is $8 B+ / yr.
Drowsy-driving regulations increasing (EU requires DMS on
new cars from 2024). Crowded — Smart Eye, Seeing Machines,
Cipia are scaled competitors with OEM deals. Entry angle:
fleet + insurance rather than OEM.

## 8. Engineer-weeks estimate

**8-12 weeks to MVP.** Weeks 1-3: copy-fork + face /
eye / gaze tracker integration. Weeks 4-6: drowsiness /
distraction / incapacitation classifiers. Weeks 7-10:
dispatcher dashboard + escalation flow. Weeks 11-12: pilot
with a small regional fleet.

## 9. Risk flags

- **Driver-privacy backlash.** Teamster unions in US have
  fought in-cab cameras — pilot carefully with union
  consent. EU works councils similar.
- **Automatic emergency calls.** Get them wrong and you
  cry wolf to 112 / 911 — dispatch services will block
  your app. Very conservative thresholds + human-in-the-
  loop confirmation.
- **OEM gatekeeping.** Major OEMs prefer their in-house
  DMS (Tesla Cabin Camera, Ford BlueCruise). Aftermarket
  fleet segment is more open.
- **Biometric-law patchwork.** Illinois BIPA has won
  multi-million-dollar class actions against facial-biometric
  products. Explicit consent + no facial-print storage is
  table stakes.

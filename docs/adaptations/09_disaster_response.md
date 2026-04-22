# 09 — Civilian disaster response

Earthquakes, floods, hurricanes, building collapse.
Mass-casualty incident triage at a civilian-response scale,
not a battlefield one. Closest cousin to the flagship.

## 1. Use case

NGO or municipal response team deploys triage4-style
capability in the first 48-72 hours after a major natural
disaster. Drones + handheld cameras + medic-tablets form the
same pipeline: find casualties → rapid triage → trauma
assessment → coordinate medic handoff. Denied-comms CRDT
sync is central here because cell towers are down.

## 2. Who pays

- International NGOs (Red Cross / Red Crescent, MSF,
  International Rescue Committee).
- National disaster-response agencies (FEMA, THW, EMERCOM).
- UN OCHA and UNICEF for humanitarian deployments.
- City-level first-responder training programmes.

Revenue model: grant-funded + one-off contracts. NOT a
self-sustaining commercial product.

## 3. What transfers from triage4

**~90 % reuse — the highest of any candidate.** This is
essentially triage4 with civilian framing.

- Everything from the triage4 stack.
- Especially: `integrations/crdt_graph.py` (central here),
  `integrations/marker_codec.py` (offline physical-marker
  handoff on casualties when CRDT can't sync), multi-
  platform manager.
- `world_replay/*`, `mission_coordination/*`.
- Platform bridges — the Tello + ROS2 + PyMAVLink work
  continues unchanged.
- Dev infrastructure.

## 4. What has to be built

- **Language pass** — "battlefield" → "disaster-zone".
  "Immediate / delayed / minimal" stays (START-protocol
  aligned). Public-facing copy rewritten from
  military-medical to humanitarian.
- **Civilian-triage tag schema** — START + JumpSTART (for
  pediatric casualties) encodes different priorities than
  pure battlefield triage. Need tag conversion.
- **Family-reunification workflow** — once someone is
  triaged, the system tracks them to the hospital so
  relatives can locate them. NEW data flow, not in triage4.
- **Multi-organisation coordination** — Red Cross + local
  EMS + military + UN all operate at the same incident.
  Shared view requires cross-organisation trust + ACL
  layer.

## 5. Regulatory complexity

**Medium.** Same clinical-adjacent posture as triage4 — it
aids medics, doesn't diagnose. But civilian humanitarian
contexts add data-protection rules (ICRC code of conduct
requires strict consent, minimal data retention) that
military doesn't. Host-country health-data laws apply
(Türkiye has strict rules; US hurricane zone doesn't).

## 6. Data availability

**Low.** No mass-casualty video datasets exist ethically.
Past disaster footage belongs to news organisations under
restrictive licences. Simulated-exercise data from
training centres is the primary calibration source (FEMA
Incident Command System training uses actors).

## 7. Commercial viability

**Low.** Grant-funded, not commercial. However: high
mission alignment with triage4's flagship posture, high
visibility (disaster responses get media attention), and
a natural bridge to the eventual military-grade Phase 11
deployment. Not a revenue product but a credibility product.

## 8. Engineer-weeks estimate

**3-5 weeks to MVP.** Shortest of any candidate:

- Weeks 1-2: language pass, tag-schema conversion (START
  + JumpSTART), civilian handoff templates.
- Weeks 3-4: family-reunification data flow.
- Week 5: one tabletop-exercise calibration with a partner
  (Red Cross training division).

## 9. Risk flags

- **Overreach into operational control.** The system
  supports responders; it does not assign resources. That
  is an operational-command role that the incident commander
  performs with the system's output.
- **Data-protection in host country.** Turkey, China, etc.
  have strict rules on what can be collected during
  disasters. Deployments must respect local law even when
  the NGO is international.
- **Use in active-conflict zones.** If deployed to a
  conflict zone, the system becomes dual-use. Requires
  legal review per deployment because of arms-export
  regulations (US ITAR, EU dual-use).
- **Funding dependency.** Grant cycles are 6-18 months;
  sustained development requires multiple rolling grants
  rather than a single commercial launch.

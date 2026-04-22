# 05 — Telemedicine pre-screening

Remote patient first-contact before a clinician call. Rural
health, NGO outreach, emergency pre-triage when hospital access
is limited.

## 1. Use case

A patient uses a phone / laptop camera + microphone to record a
1-2 minute structured self-report. The system extracts
stand-off vitals (HR, breathing rate), postural + motion
signatures, acoustic markers (cough quality, vocal strain),
and packages a summary for the receiving clinician. The
clinician reviews the summary BEFORE the teleconsult and
decides priority (urgent / schedule / self-care). **The system
never diagnoses.**

## 2. Who pays

- Telehealth providers (Teladoc, Amwell, Babylon Health).
- Rural-health NGOs (Partners In Health, Médecins Sans
  Frontières, Mercy Ships).
- National health services for remote-outreach programmes
  (NHS Digital, Canada First Nations Health Authority).
- Emergency-medical triage programmes (ambulance-dispatch
  decision support).

Revenue model: SaaS per seat for providers + grant funding for
NGOs.

## 3. What transfers from triage4

**~85 % reuse — highest of any candidate.** The code path is
almost identical; the framing changes.

- Everything from the triage4 perception / signatures /
  reasoning stack.
- `marker_codec` for offline-capable handoff in
  denied-connectivity rural settings.
- `FrameSource`, platform bridges (WebSocket), etc.
- Dev infrastructure.

## 4. What has to be built

- **Patient-facing structured-self-report flow** — a guided
  UX (stand here, show your hands, cough once, say "aah")
  replacing the operator-facing dashboard.
- **Clinician dashboard** — different information density
  than triage4's; adds patient-reported symptoms, medical
  history, prior consults.
- **EHR integration adapter** (FHIR / HL7) for sending
  summaries into existing clinical systems.
- **Claims-discipline rewrite** — this is clinical-adjacent,
  so every word is audited by a regulatory consultant, not
  just by `claims_lint.py`. "Priority" becomes "escalation
  recommendation for clinician review".

## 5. Regulatory complexity

**HIGH — the blocker.** Even though code reuse is ~85 %, the
regulatory work is a full product-development cycle in
itself:

- FDA SaMD Class II (US) — enhanced-documentation 510(k).
  12-18 months.
- EU MDR Class IIa — Notified Body required. Same timeline.
- HIPAA (US) / GDPR Article 9 (EU special-categories) —
  infrastructure-level changes: BAAs with every vendor,
  encryption at rest, audit logs, data-residency controls.
- IEC 62304 Class B lifecycle — formal SRS, design-FMEA,
  clinical-evaluation plan.

Add **12+ engineer-weeks of non-coding regulatory work** to
whatever the code estimate says, plus one qualified regulatory
consultant full-time, plus a clinical-advisory board.

## 6. Data availability

**Low without a partner, high with one.** Public datasets
(MIMIC-III, BIDMC) exist via PhysioNet with academic
agreements. Symptomatic video / audio — essentially zero
public data; everything comes from a clinical-research
partnership.

## 7. Commercial viability

**Medium-high.** Telehealth is a large market ($50 B+ / yr),
but well-funded incumbents (Teladoc, Amwell) already dominate
pre-triage. Entry requires a clinical-angle differentiator —
the grounded-explanation pattern from triage4 is one
possibility ("HR elevation could be explained by anxiety;
review the breathing-pattern panel before escalating").

## 8. Engineer-weeks estimate

**4-8 weeks for code + 12-24+ weeks for regulatory + 12 months
for clinical validation.** Total real timeline: 18-36 months
to a shippable product. Code is not the long pole.

## 9. Risk flags

- **Regulatory underestimation.** Every entrepreneur who says
  "we'll do SaMD later" is in for a 6-12 month surprise.
  Don't start without a regulatory consultant already
  engaged.
- **Clinical safety.** A pre-triage tool that under-triages
  an MI or stroke causes real harm. Calibration must be done
  against labelled clinical data, not synthetic.
- **Liability insurance.** $5-10M clinical-errors-and-omissions
  coverage typical; budget accordingly.
- **Data-breach exposure.** PHI in a breach costs $10M+ in US
  regulatory fines per incident. Security review mandatory
  before any beta.
- **Park it** until a clinical partner appears. Without one,
  the data-availability and regulatory blockers make this the
  wrong first sibling.

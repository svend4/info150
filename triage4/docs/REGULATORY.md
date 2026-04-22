# triage4 — Regulatory landscape

Non-binding regulatory awareness document for the **triage4** stack.
Scope: what rules apply *if* the project ever moves from
decision-support research code toward a medical product — and how the
current architecture already anticipates those rules.

**This document is not legal advice and triage4 is not a medical
device.** Any clinical deployment requires a qualified regulatory
consultant, a Quality Management System (QMS), and jurisdiction-
specific submissions.

## 1. Current framing

triage4 is framed, both in code and in documentation, as **autonomous
*decision-support*** for first-responder workflows. Every external
surface (ONE_PAGER, ARCHITECTURE, darpa_mapping) repeats three claims:

1. triage4 does *not* diagnose.
2. triage4 does *not* replace a medic.
3. Every output is accompanied by per-channel confidence and
   explanation so a human can override it.

These three claims place the current codebase in the same regulatory
band as a **clinical-decision-support (CDS) research tool**, not a
`Software as a Medical Device` (SaMD) under FDA / EU MDR rules.

The remainder of this document describes the rules that *would* apply
if framing changed.

## 2. Jurisdictions to plan for

| Jurisdiction | Framework | Primary pathway |
|---|---|---|
| USA | FDA 21 CFR 820 / Software Precertification / 510(k) | Premarket notification or De Novo |
| EU | EU MDR 2017/745 | Notified-Body conformity assessment |
| UK | UK MDR 2002 (amended) | UKCA marking via Approved Body |
| Canada | SOR/98-282 | Licence by class (II–IV) |
| International | IMDRF / IEC 62304 / ISO 14971 / ISO 13485 | Harmonised standards |

triage4's design target is **international conformance via IMDRF
harmonised standards**, then bespoke marking per jurisdiction.

## 3. SaMD classification (IMDRF framework)

The IMDRF N12 risk matrix classifies SaMD by `(healthcare situation) ×
(significance of information)`:

| Situation / significance | Inform mgmt | Drive mgmt | Diagnose / treat |
|---|---|---|---|
| Non-serious | I | II | II |
| Serious | II | III | III |
| **Critical (life-threatening)** | **III** | **III** | **IV** |

triage4's target use case (mass-casualty / battlefield triage) is
**critical** on the situation axis. On the information axis the
current "decision support + human in the loop + explainability"
framing puts it at "inform clinical management", giving a target class
of **SaMD III** — the same band as CAD (computer-aided detection)
triage systems for stroke / PE.

Moving to fully autonomous priority assignment without a human in the
loop would push the information axis to "drive / diagnose" and the
class to **SaMD IV**, which is substantially harder to clear.

**Design implication:** keep `autonomy/human_handoff.py` on the
critical path, keep operator override working end-to-end, and never
auto-administer any intervention. triage4 currently honours all three.

## 4. IEC 62304 software lifecycle

IEC 62304 is the harmonised standard for medical-device software and
is referenced by both FDA and EU MDR. It defines three safety classes:

- **A** — no injury possible
- **B** — non-serious injury possible
- **C** — serious injury or death possible

A stand-off triage system that influences mortal-sign escalation is
**Class C** under any reasonable failure-mode analysis.

### Class C required artefacts (summary)

| Clause | Artefact | Current triage4 state |
|---|---|---|
| 5.1 | Software development plan | `docs/ROADMAP.md`, `CHANGELOG.md` |
| 5.2 | Software requirements | partial — `docs/ARCHITECTURE.md`, `darpa_mapping.md` |
| 5.3 | Software architecture | `docs/ARCHITECTURE.md` (K3 matrix) |
| 5.4 | Detailed design | per-module docstrings, `docs/API.md` |
| 5.5 | Unit implementation + verification | 487 tests, mypy, ruff |
| 5.6 | Integration + integration testing | `tests/test_end_to_end.py` |
| 5.7 | System testing | `examples/full_pipeline_benchmark.py` |
| 5.8 | Release | not started — no clinical release yet |
| 6.x | Problem resolution | GitHub issues (hypothetical) |
| 7.x | Risk management | `docs/RISK_REGISTER.md`, `docs/SAFETY_CASE.md` |
| 8.x | Configuration management | git, tagged releases |
| 9.x | Problem / change resolution | `CHANGELOG.md`, PR reviews |

**Gap to Class C readiness:**

1. Formal software-requirements specification (SRS) — separate doc,
   linked to every module.
2. Design-FMEA — partially covered by `RISK_REGISTER.md`, needs
   full-form entries per hazard.
3. Clinical-evaluation plan — requires a clinical partner (Phase 11).
4. Post-market surveillance plan — requires a deployment (Phase 13).

## 5. FDA-specific pathway (hypothetical)

If triage4 were ever submitted to FDA, the most likely route is:

- **De Novo request** — no predicate device for autonomous stand-off
  triage; De Novo establishes a new classification.
- **Alternatively 510(k)** if a predicate is found (e.g. an existing
  CDS-class triage support tool).

Supporting submissions required:
- **510(k) / De Novo summary** — product description, substantial-
  equivalence argument or novelty argument.
- **Software documentation** — per FDA "Content of Premarket
  Submissions for Device Software Functions" (2023 guidance), the
  "Enhanced Documentation" level, given Class III.
- **Cybersecurity documentation** — per "Cybersecurity in Medical
  Devices: Quality System Considerations" (2023 guidance): SBOM,
  threat model, penetration-test report. triage4 already targets the
  SBOM side (pure stdlib + numpy + scipy core).
- **Clinical performance data** — prospective or retrospective study
  against gold-standard triage labels. Phase 11 dependency.

## 6. EU MDR specifics (hypothetical)

- **Class IIb / III** under Annex VIII rules, depending on whether
  output is treated as "diagnostic" or "decision-support".
- **Notified Body** conformity assessment required at Class IIb+.
- **Unique Device Identifier (UDI)** registration in EUDAMED.
- **Technical Documentation** per Annex II + Annex III.
- **Clinical Evaluation Report (CER)** per MDCG 2020-13.
- **Post-Market Clinical Follow-up (PMCF)** plan.

## 7. AI/ML-specific considerations

triage4 is *mostly* deterministic (heuristic fusion + hand-wired
classifier + particle filter). The one adaptive component is the
`PatientTwinFilter`, which updates posteriors from observations but
does not self-train. This puts triage4 at the *locked-algorithm* end
of the FDA / IMDRF AI spectrum — simpler to clear than a
continuously-learning system.

If neural-network components are added later (e.g. a trained YOLO
detector via `build_ultralytics_detector`), the following apply:

- **FDA Predetermined Change Control Plan (PCCP)** — declare up-front
  what can retrain without re-submission.
- **IMDRF Good Machine Learning Practice (GMLP)** — 10 guiding
  principles for ML-powered medical devices (2021).
- **Transparency** — every ML output must be accompanied by the
  training-data description, performance metrics, and known bias
  modes.

triage4 already has `triage_reasoning/llm_grounding.py` that rules out
LLM-driven clinical decisions by construction. That architectural
choice would be documented as a safety claim in a submission.

## 8. Data-protection overlay

Separate from medical-device regulation, any clinical pilot must
handle:

- **HIPAA** (US) — Privacy Rule + Security Rule for PHI at rest /
  in transit.
- **GDPR** (EU) — Article 9 (special categories), Article 32
  (security), DPIA for high-risk processing.
- **Common Rule / ICH-GCP** — for any prospective study.

triage4 currently handles *synthetic* data only; no real PHI is in
the repo, in tests, or in any example script. The `marker_codec`
module uses HMAC-SHA256, which is pre-approved by FIPS 180-4 and
acceptable under both HIPAA Security Rule and GDPR Art 32.

## 9. Claims discipline

The following words are **not** used in the triage4 README, docstrings,
or UI copy, because each carries regulatory weight:

- ❌ "diagnose" / "diagnosis"
- ❌ "treat" / "treatment"
- ❌ "clinical" (without "decision-support" qualifier)
- ❌ "medical device"
- ❌ "FDA-cleared" / "CE-marked"

Allowed framing:

- ✅ "decision-support"
- ✅ "triage priority recommendation"
- ✅ "stand-off observation"
- ✅ "research / non-clinical"

A future CI check (`.github/workflows/claims-lint.yml`) could enforce
this against every `*.md` and `*.py` docstring. Not yet implemented.

## 10. Checklist before a clinical pilot

- [ ] Formal SRS (software-requirements specification) per module
- [ ] Completed design-FMEA with traceability from hazard → test
- [ ] ISO 14971 risk-management file
- [ ] ISO 13485 QMS in place (or bridge to a partner's QMS)
- [ ] Clinical-evaluation plan reviewed by regulatory consultant
- [ ] IRB / ethics approval at the partner site
- [ ] Data Use Agreement for any real patient data
- [ ] Cybersecurity threat model + penetration test
- [ ] SBOM (`pip-compile`, `cyclonedx-py`) attached to release
- [ ] Claims review of all user-facing copy
- [ ] Informed-consent language for participants
- [ ] Post-market surveillance plan with adverse-event reporting

## 11. What triage4 already does right

- **Decision-support framing** consistent across code, docs, and UI.
- **Human-in-the-loop** is non-optional — `autonomy/human_handoff.py`
  is on the critical path.
- **Explainability** is always on — every triage output carries
  reasons + per-channel confidence.
- **Deterministic by default** — the one probabilistic component
  (`PatientTwinFilter`) uses fixed seeds and returns posteriors
  rather than point estimates.
- **SBOM-friendly** — pure stdlib + numpy + scipy + fastapi core,
  all under permissive licences.
- **No PHI in the repo** — synthetic data only.
- **Integrity at the edge** — `marker_codec` uses FIPS-approved HMAC.
- **Tests as specification** — 487 tests lock behaviour, including
  the critical "mortal-sign override never regresses" invariant.

## 12. References

- IEC 62304:2006/AMD 1:2015 — Medical device software
- ISO 14971:2019 — Application of risk management to medical devices
- ISO 13485:2016 — Medical devices QMS
- IMDRF N12 (2014) — Software as a Medical Device: Possible Framework
  for Risk Categorization
- IMDRF/MLMD WG/N88 (2022) — Machine Learning-enabled Medical Devices
- FDA (2023) — Content of Premarket Submissions for Device Software
  Functions
- FDA (2023) — Cybersecurity in Medical Devices: Quality System
  Considerations
- MDCG 2019-11 — Qualification and Classification of Software
- MDCG 2020-13 — Clinical Evaluation Assessment Report Template
- GMLP (2021) — FDA/Health Canada/MHRA joint Good ML Practice
- FIPS 180-4 — Secure Hash Standard (SHA-256)

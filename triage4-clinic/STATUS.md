# triage4-clinic — status

Honest accounting. Marketing stays out.

## Built

- Package scaffold (`pyproject.toml`, `Makefile`, `.gitignore`).
- `docs/PHILOSOPHY.md` — grounded-alternatives posture,
  SaMD-adjacent regulatory scaffolding, forking
  pathway.
- `triage4_clinic.core`:
  - `enums`: `EscalationRecommendation` (self_care /
    schedule / urgent_review), `ChannelKind`
    (cardiac / respiratory / acoustic / postural /
    reporting), `ExplanationLikelihood` (possible /
    plausible / likely), `CaptureQuality` (good /
    noisy / partial).
  - `models`: `VitalsSample`, `AcousticSample`,
    `CoughSample`, `PostureSample`, `PatientSelfReport`,
    `PatientObservation`, `ChannelReading` (carries
    `signature_version`), `AlternativeExplanation`,
    `PreTriageAssessment`, `ClinicianAlert` (with
    grounded-alternatives positive requirement +
    reasoning-trace + negative forbidden-lists),
    `PreTriageReport`.
- `triage4_clinic.signatures`:
  - `cardiac_readings` — HR vs. adult band + reliability
    flag. Generates paired alternative explanations for
    elevated readings (anxiety, exertion, cardiac concern).
  - `respiratory_readings` — RR vs. adult band + cough
    frequency from acoustic window. Paired alternatives
    (respiratory infection, asthma, anxiety).
  - `acoustic_strain` — vocal strain from sustained
    "aah" window. Paired alternatives (upper-respiratory,
    dehydration, vocal effort).
  - `postural_stability` — balance pattern. Paired
    alternatives (general weakness, vestibular, medication-
    related balance).
- `triage4_clinic.clinic_triage`:
  - `adult_clinical_bands` — adult reference vitals
    bands (HR 60-100 / RR 12-20) + tunable thresholds.
  - `triage_engine.ClinicalPreTriageEngine.review(
    observation, self_report)` → `PreTriageReport`.
- `triage4_clinic.sim`:
  - `synthetic_self_report` — deterministic self-report
    generator.
  - `demo_runner` — `make demo` entry point.
- `tests/` — model / signature / engine coverage.

## Not built

- **Stand-off vital extraction.** Upstream (Eulerian
  magnification for HR, chest-motion FFT for RR) lives
  in the consumer app; this library consumes already-
  extracted `VitalsSample` values.
- **Acoustic feature extraction.** Upstream cough
  classifier + vowel-strain feature extractor live in
  the consumer app.
- **Patient-facing UX.** The "stand here, show your
  hands, cough once, say aah" guided flow is consumer-
  app responsibility.
- **Clinician dashboard / EHR integration.** The library
  produces `PreTriageReport`; FHIR / HL7 serialisation
  + dashboard lives downstream.
- **Actual SaMD clearance.** The library is architected
  for audit readiness (reasoning trace, signature
  versioning, grounded alternatives) but it is NOT
  cleared as a medical device.
- **HIPAA-compliant infrastructure.** That's an
  infrastructure-layer concern handled by the
  deployment, not the library.
- **Clinical validation study.** The
  DOMAIN_ADAPTATIONS file flags 12 months + clinical
  partnership as the real path to shipping.
  Thresholds here are adult-reference literature
  values, NOT clinically validated.

## Scope boundary (repeated for emphasis)

- **No diagnosis.** The library never asserts a
  diagnosis. "HR elevated" is reported; "tachycardia"
  (even as a signal label) is avoided in output text.
- **No treatment.** No prescription / medication /
  procedure recommendations.
- **No regulatory over-claim.** The library must not
  claim FDA clearance, medical-device status, or SaMD
  certification.
- **Default to schedule, not self_care.** An absence
  of strong signals does NOT mean the patient is fine
  — it means the library did not surface urgent
  signals in this 1-2 minute window. The default
  escalation is `schedule`, never `self_care`.
- **Grounded alternatives required.** Every
  `ClinicianAlert` must enumerate plausible alternative
  explanations — enforced at dataclass construction.

If a future version produces actual diagnoses or
treatment recommendations, that work crosses the
SaMD-clearance line and belongs in a regulated
downstream product. Don't erode inside this codebase.

# triage4-clinic

Telemedicine pre-screening support library — **tenth sibling**
in the triage4 monorepo. Consumes a 1-2 minute structured
patient self-report (stand-off vitals + acoustic markers +
postural samples) and produces a **clinician-facing**
pre-consult summary with escalation recommendation.

Highest code reuse of any sibling in the catalog (~85 %)
but also the highest regulatory complexity — this is SaMD-
adjacent territory (FDA Class II, EU MDR Class IIa, HIPAA,
GDPR Article 9). The library is not SaMD-cleared; it is
architected to **be ready** for the regulatory work a
consumer app would have to do before shipping clinically.

Domain framing comes from the
[telemedicine pre-screening](../docs/adaptations/05_telemedicine_pre_screening.md)
adaptation study.

## What's architecturally different about this sibling

Every prior sibling's claims guard is a **negative**
constraint — a forbidden-vocabulary list that raises at
construction if matched. This sibling adds a **positive**
requirement:

**Every `ClinicianAlert` MUST carry one or more
alternative explanations** for the signal it surfaces.

The library's output never says "HR elevated → cardiac
concern". It says "HR elevated. Candidate explanations:
anxiety (plausible); recent exertion (plausible);
cardiac concern (possible, requires exam)." The
clinician decides. That phrasing is enforced at the
dataclass level — a `ClinicianAlert` without alternatives
raises `ValueError`.

Two supporting architectural features make the sibling
audit-ready even though it isn't SaMD-cleared:

- **Reasoning trace**. Every alert carries a
  `reasoning_trace` — a short structured string naming
  the signatures and thresholds that drove the alert.
  Designed to survive a regulatory audit review.
- **Signature versioning**. Every `ChannelReading` carries
  a `signature_version` tag so a retrospective review can
  tie an output to the exact signature code that produced
  it.

## What it is

- A library that consumes already-extracted
  `VitalsSample`, `AcousticSample`, `PostureSample`,
  `CoughSample` records from an upstream capture layer
  (phone camera + microphone) and emits:
  - **Cardiac readings score** — HR vs. adult bands with
    arrhythmia-indeterminate flagging.
  - **Respiratory readings score** — RR vs. adult bands
    + cough frequency from acoustic window.
  - **Acoustic-strain score** — vocal strain from
    sustained-vowel recording ("aah").
  - **Postural-stability score** — balance + sway during
    the "stand here" portion of the structured flow.
- A `ClinicalPreTriageEngine` that fuses the four
  channels, attaches grounded alternative explanations
  to every surfaced alert, and produces:
  - A `EscalationRecommendation` (`self_care` /
    `schedule` / `urgent_review`) for the clinician.
  - Zero-or-more `ClinicianAlert` records, each with
    alternative explanations + reasoning trace.
- A deterministic synthetic-self-report generator so
  tests and demos work without PHI.

## What it is not

- **Not a diagnostic device.** The library never
  asserts a diagnosis. "HR elevated" is reported; "the
  patient has tachycardia / has anxiety / has cardiac
  disease" is not.
- **Not FDA-cleared.** This library is not a SaMD. It is
  an upstream component a consumer app MAY use as part
  of a SaMD-cleared product. That work belongs
  downstream.
- **Not a replacement for a clinician.** The escalation
  tier is for clinician-review routing. It never tells
  a patient "you do not need to be seen" or "you have
  nothing to worry about". Absence of alerts defaults
  to `schedule`, never to `self_care`.
- **Not an EHR.** The library produces structured
  `PreTriageReport` records. FHIR / HL7 serialisation
  lives downstream.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-clinic (telemedicine)       |
|---------------------------------|--------------------------------------|
| `CasualtyNode`                  | `PatientObservation` (opaque token)  |
| `triage_priority` (1-4)         | `EscalationRecommendation` (self_care / schedule / urgent_review) |
| `RapidTriageEngine`             | `ClinicalPreTriageEngine`            |
| `MortalThresholds`              | `AdultClinicalBands`                 |
| `MedicHandoff`                  | `PreTriageReport` (FHIR-serialisable downstream) |
| "medic"                         | "clinician"                          |
| "battlefield"                   | "pre-consult" / "self-report"        |

## Claims guard + positive requirement

`ClinicianAlert` enforces:

**Negative (forbidden)**:
- Definitive diagnosis: "diagnosis of", "confirms",
  "the patient has", "is a case of".
- Treatment: "prescribe", "administer", "take",
  "start medication".
- Regulatory over-claim: "FDA-cleared", "medical
  device", "SaMD", "clinically validated", "diagnoses",
  "replaces clinician".
- Reassurance: "you are fine", "no need for review",
  "can skip the visit".
- Patient identity: "patient <firstname>" heuristic.

**Positive (required)**:
- Non-empty `alternative_explanations` tuple with at
  least one entry.
- Non-empty `reasoning_trace` string.
- Non-empty `signature_version` string on each upstream
  `ChannelReading`.

See `docs/PHILOSOPHY.md`.

## Copy-fork architecture

Still copy-fork. Zero imports from `triage4` or any
other sibling. Ten concrete copy-forks now — the
shared-core extraction conversation from
`DOMAIN_ADAPTATIONS §7` is now sourced from ten real
codebases. Still a separate effort; still not this
sibling's scope.

## See also

- `docs/PHILOSOPHY.md` — grounded-alternatives posture,
  regulatory scaffolding, forking pathway.
- `STATUS.md` — honest accounting.
- [`docs/adaptations/05_telemedicine_pre_screening.md`](../docs/adaptations/05_telemedicine_pre_screening.md)
  — parent adaptation study (with the "park until a
  clinical partner appears" risk flag).

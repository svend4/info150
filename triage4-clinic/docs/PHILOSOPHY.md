# Philosophy — grounded alternatives, audit-ready

triage4-clinic is the first sibling where the claims guard
carries a **positive** requirement, not just a negative
constraint.

Every `ClinicianAlert` the library emits MUST carry a
non-empty tuple of alternative explanations for the signal
it surfaces. The library's output never says "HR elevated →
cardiac concern". It says "HR elevated. Candidate
explanations: anxiety, recent exertion, cardiac concern.
Clinician review recommended." The clinician decides.

Three empirical failure modes this positive requirement
prevents:

1. **Narrow-inference anchoring.** A pre-consult tool that
   frames an elevated HR as a single possibility
   ("cardiac concern") anchors the clinician's thinking
   before they see the patient. Listing plausible
   alternatives explicitly disrupts the anchor and
   returns the differential-diagnosis work to where it
   belongs.
2. **Diagnostic-illusion risk.** A layperson reading a
   pre-consult summary ("system flags possible cardiac
   concern") can treat it as a diagnosis the library is
   not authorised to make. Surrounding the signal with
   alternatives makes it unambiguous that the library is
   observing, not concluding.
3. **Audit-trail weakness.** An FDA / EU MDR reviewer
   reading a cleared product's alerts wants to see
   evidence that the product didn't pretend to diagnose.
   Alternatives in the output stream are part of that
   evidence.

## Why the sibling is audit-ready but not SaMD-cleared

The DOMAIN_ADAPTATIONS file is explicit: this sibling is
the highest-regulatory-complexity candidate in the
catalog, and the parent adaptation author's
recommendation is "park it until a clinical partner
appears". The library exists as a pattern exploration —
proof that the copy-fork architecture can produce code
READY for SaMD-style regulatory work, without claiming
the work has been done.

Two supporting architectural features:

- **Reasoning trace**. Every `ClinicianAlert` carries a
  `reasoning_trace` string that names the signatures and
  thresholds that drove the alert. Designed to survive a
  regulatory audit review — the reviewer can retrace from
  output text back to engine logic.
- **Signature versioning**. Every `ChannelReading` carries
  a non-empty `signature_version` field. When a signature
  is re-tuned, the version bumps and historical outputs
  can be tied to the exact code that produced them.

## The negative forbidden lists

### Clinical — definitive diagnosis

- "diagnosis of", "diagnosis:", "confirmed diagnosis"
- "the patient has", "is a case of"
- "confirms a"
- "diagnosis is"

Rationale: the library is architected to be an input to a
clinician, not a clinician itself. Diagnosis is a licensed
act; the library never asserts one.

### Clinical — treatment

- "prescribe", "prescribed"
- "administer"
- "start medication"
- "take this drug"
- "treatment:"

Rationale: treatment is a licensed act. Even for a
cleared SaMD, treatment recommendations add a separate
Class III regulatory tier this library's architecture
does not aspire to.

### Regulatory over-claim

- "fda-cleared", "fda cleared"
- "medical device"
- "samd", "samd-certified"
- "clinically validated"
- "diagnoses" (as a verb describing the library)
- "replaces clinician", "replaces the clinician"

Rationale: the library must not claim what it isn't.
Consumer apps building a cleared product make those
claims; the library itself does not.

### Reassurance

- "you are fine"
- "no need for review"
- "can skip the visit"
- "no clinical concerns"
- "all vital signs normal"
- "nothing unusual"

Rationale: default-schedule behaviour plus the
no-reassurance list together enforce the product
posture that absence of surfaced alerts is NOT a
clearance of the patient.

### Patient identity

- "patient <firstname>" pattern heuristic.

Rationale: PHI never leaves the library. Names, DOB,
addresses all flow through a separate consent-gated
layer.

## The positive requirement

`ClinicianAlert.__post_init__` additionally requires:

- `alternative_explanations` tuple non-empty
- `reasoning_trace` string non-empty
- each `AlternativeExplanation.text` non-empty + passes
  a light claims-guard (no definitive language inside
  an alternative either — "could be anxiety" is fine,
  "is anxiety" is not).

## What gets reused from triage4

Conceptual, not literal.

- Everything from the perception / signatures /
  reasoning stack concepts.
- Claims-guard dataclass shape.
- Test conventions, deterministic crc32 seeds.
- Synthetic-fixture pattern — essential here because
  real PHI cannot be committed to an open-source repo.

## What does NOT get reused

- triage4's `REGULATORY.md` — written for SaMD-adjacent
  military medicine. This sibling's regulatory framing
  is different (telehealth-specific), though the shape
  of the document would transfer.
- Single-output-dataclass engine pattern — replaced by
  an engine that produces a structured `PreTriageReport`
  with multi-alert + assessment.

## When these lines move

- If a future version issues actual diagnoses → SaMD
  clearance required; fork to a separate regulated
  codebase with all the 12-18 month + clinical-partner
  work the adaptation file describes.
- If a future version produces treatment
  recommendations → SaMD Class III territory; very
  separate product.
- If a future version integrates directly with EHR
  systems → FHIR / HL7 serialisation belongs in a
  consumer-app adapter, not this library.

## In short

Positive requirement, not just negative forbiddens.
Grounded alternatives are load-bearing. Reasoning trace
is load-bearing. Signature versioning is load-bearing.
The clinician is the product; the library is an input
to a regulated product a consumer app may build.

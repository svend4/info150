# Philosophy — wellness, not clinical

Why triage4-desk exists as a **separate package** rather than a
module inside triage4.

## The hard boundary

triage4 is a **decision-support system for DARPA-class triage**.
It lives inside a regulatory posture (SaMD-adjacent, IEC 62304
Class C analysis, ISO 14971 risk register) that shapes every line
of code: forbidden vocabulary, mandatory explanations, mortal-
sign overrides, clinical claim discipline.

triage4-desk is a **consumer wellness library**. It has zero
regulatory surface. It produces coaching suggestions. A trainer
or a user ignores them, modifies them, or acts on them as they
see fit.

These two products **must not live in the same process.** Why:

1. **Claims bleed.** A process that imports `triage4` carries
   triage4's regulatory framing to every observer. An auditor
   reviewing a deployment will treat the fitness UI and the
   triage UI as one product. That risks either:
   - triage4 being watered down to "consumer wellness" (losing
     its decision-support posture), or
   - triage4-desk being pushed into clinical framing (triggering
     SaMD requirements it never needs).
2. **Data bleed.** A casualty graph containing real-or-simulated
   patients cannot co-exist with a fitness session history in
   the same storage layer. The regulatory overhead of a clinical
   data store (encrypted at rest, BAAs, access logs, retention
   limits) swamps the wellness use case.
3. **Language bleed.** The `claims_lint.py` script in triage4
   forbids "diagnose" / "treat" / "FDA-cleared". Those are
   irrelevant for fitness — but a trainer saying "diagnose your
   form" is *routine* English. Two different lint configs, two
   different vocabularies, two different processes.

## What gets reused

The DOMAIN_ADAPTATIONS.md index estimates 65 % code reuse from
triage4 for fitness. That reuse is **conceptual**, not literal:

- `FrameSource` pattern (but the fitness sibling doesn't import
  from triage4 — it copies the pattern).
- Eulerian vitals approach (Butterworth bandpass on pooled
  luminance — same math, different HR band).
- Pose-symmetry idea (same math as K3-1.3 skeletal asymmetry —
  different joint topology, different threshold calibration).
- Grounded explanation pattern (LLM-free template backend by
  default).
- `claims_lint` script adapted to fitness vocabulary.
- Test conventions (hypothesis for properties, fixed seeds,
  no time-based tests).

## What does NOT get reused

- Larrey baseline — 1797 battlefield medicine is irrelevant to
  gym.
- Mortal-sign override — there is no "mortal sign" in wellness.
- Mission graph / casualty graph — fitness is per-session, not
  per-mission.
- DARPA gate evaluators — not applicable.
- `REGULATORY.md`, `SAFETY_CASE.md`, `RISK_REGISTER.md` — by
  design NOT copied. This product is consumer wellness.

## When this line moves

If a future version of triage4-desk gets "injury prediction" as a
headline claim, that crosses into clinical territory. At that
point the right move is:

1. Fork **triage4-desk-medical** as a third sibling.
2. Move the injury-prediction surface there.
3. Add the full regulatory-document set to the medical sibling.
4. Keep triage4-desk a pure wellness product.

Don't gradually erode the wellness / clinical boundary inside
one codebase. It always ends in compliance pain.

## In short

Same decision-support *infrastructure*. Different decision-
support *posture*. Different products. Different audiences.
Different legal surfaces. Different directories.

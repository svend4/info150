# triage4 — Safety case

Structured safety argument for the **triage4** decision-support stack,
following the Goal-Structuring-Notation (GSN) pattern: top goal,
sub-goals, strategy, evidence. Pre-clinical; the evidence items are
software-level, not clinical.

Terminology (GSN short form):
- **G** — Goal (a claim to be argued)
- **S** — Strategy (how the argument proceeds)
- **C** — Context / assumption
- **J** — Justification
- **Sn** — Solution / evidence

## Top goal

**G0 — triage4 is safe to run as decision-support in a research /
pre-clinical setting, provided every output is reviewed by a qualified
operator before any real-patient action.**

### Context

- **C0.1** Target users are trained medics or SAR personnel in
  stand-off triage scenarios.
- **C0.2** No real-patient data in the repo, tests, or examples.
- **C0.3** No clinical claims; decision-support framing is enforced
  in docs (see `REGULATORY.md §9`).
- **C0.4** No autonomous clinical action is possible — there is no
  actuator that administers treatment.

### Strategy

**S0 — decompose into (a) output-correctness safety, (b) failure-mode
safety, (c) operator-in-the-loop safety, (d) data-integrity safety.**

---

## G1 — Output correctness

**Triage outputs are at least as safe as a trained-human baseline on
every critical case the system has been tested against.**

### S1 — argue via baseline comparison + regression tests

- **G1.1** The system never misses a mortal sign that a 1797-era
  battlefield medic would catch.
  - **Sn1.1.1** `tests/test_larrey_baseline.py` compares
    `RapidTriageEngine` against `LarreyBaselineTriage` on isolated
    mortal-sign cases. Both must hit 0% critical-miss rate.
  - **Sn1.1.2** `MortalThresholds` in `score_fusion.py` forces
    `immediate` when any single mortal channel crosses threshold,
    regardless of fused score. Tested in
    `tests/test_score_fusion.py::test_mortal_sign_override_*`.
  - **Sn1.1.3** The override reason ("mortal-sign override") is
    surfaced in the output so the operator can see *why* the jump
    happened.

- **G1.2** The system provides a posterior distribution over priority
  bands, not a point estimate, so the operator sees *uncertainty*.
  - **Sn1.2.1** `PatientTwinFilter` (200-particle Bayesian filter)
    returns `TwinPosterior` with per-band probabilities and effective
    sample size. Tested in `tests/test_bayesian_twin.py`.
  - **Sn1.2.2** Low effective sample size is surfaced as a sanity
    flag.

- **G1.3** A second, independent classifier checks the heuristic
  engine on every case.
  - **Sn1.3.1** `CelegansTriageNet` runs in parallel; disagreement
    can be surfaced to the operator.
  - **Sn1.3.2** The C.elegans network has 45 hand-authored weights,
    each inspectable — no learned parameters that could drift.

### Residual limitation

- **J1.R1** Current calibration dataset is 70 synthetic casualties
  with sensor-degradation noise. Real-world distribution may differ.
  Tracked in `RISK_REGISTER.md` row **CAL-001**.

---

## G2 — Failure-mode safety

**When a component fails or returns untrustworthy data, the system
defaults to alerting the operator rather than taking an unsafe
action.**

### S2 — argue via per-component failure analysis

- **G2.1** When sensor input is degraded, confidence is propagated
  downstream.
  - **Sn2.1.1** `UncertaintyModel.from_signature` computes
    per-channel confidence from raw-feature quality flags. Low
    quality → low confidence → operator sees it. Tested in
    `tests/test_uncertainty.py`.
  - **Sn2.1.2** `SensorDegradationSimulator` in `sim/` injects
    noise / dropout; evaluation scripts verify behaviour under
    degradation.

- **G2.2** When platform comms are denied, local state stays
  internally consistent.
  - **Sn2.2.1** `CRDTCasualtyGraph` uses OR-set + LWW-register +
    G-counter. Merges are commutative and idempotent —
    proved mathematically, tested in `tests/test_crdt_graph.py`.
  - **Sn2.2.2** `marker_codec` offers an offline fallback for
    casualty-bound handoff. HMAC rejects tampered / forged /
    replayed markers. Tested in `tests/test_phase9e.py`.

- **G2.3** When external SDKs are not installed, the pipeline still
  runs in loopback mode and CI remains green.
  - **Sn2.3.1** Every platform bridge ships as a
    `Loopback<X>Bridge` plus a lazy `build_<real>_bridge` factory
    that raises `BridgeUnavailable` if the SDK is absent.
  - **Sn2.3.2** CI leak-check asserts that no external SDK is
    imported at package load time (`test_end_to_end.py`).

- **G2.4** When the fractal mission layer detects saturation,
  operators see an escalation recommendation.
  - **Sn2.4.1** `classify_mission` returns `escalate` when
    medic utilisation ≥ 0.9 or immediate fraction ≥ 0.5, with
    human-readable reasons. Tested in `test_phase9e.py`.

---

## G3 — Operator-in-the-loop safety

**No triage decision reaches a patient without a human operator
reviewing the output and explanations.**

### S3 — argue via architectural invariants

- **G3.1** Every triage output is accompanied by a reason list and
  per-channel confidence.
  - **Sn3.1.1** `RapidTriageEngine.infer_priority` returns
    `(priority, score, reasons)`; `UncertaintyModel` returns
    `per_channel_confidence`. Both are required by the dashboard
    API contract.
  - **Sn3.1.2** `ExplainabilityBuilder` produces operator-readable
    summaries. Tested in `tests/test_explainability.py`.

- **G3.2** LLM components (if ever attached) can phrase but not
  invent clinical facts.
  - **Sn3.2.1** `LLMBackend` Protocol + `GroundingPrompt` structure
    force the LLM to operate only on numeric facts triage4 already
    decided. Default `TemplateGroundingBackend` is LLM-free.
  - **Sn3.2.2** Tests assert the prompt never loses the numeric
    context (`test_llm_grounding.py`).

- **G3.3** Operator handoff and override are on the critical path,
  not optional.
  - **Sn3.3.1** `autonomy/human_handoff.py` is always invoked when
    entropy of priority observations stabilises
    (`triage_temporal/entropy_handoff.py`).
  - **Sn3.3.2** `hmt_lane` evaluation tracks handoff timeliness,
    agreement, and override rate.

### Residual limitation

- **J3.R1** triage4 is *software-only*. Physical handoff depends on
  a real dashboard / radio / UI. UI correctness is out of scope for
  this safety case. Tracked in `RISK_REGISTER.md` row **UI-001**.

---

## G4 — Data-integrity safety

**Data passing between system components cannot be silently corrupted
or spoofed.**

### S4 — argue via crypto + schema

- **G4.1** Offline markers cannot be tampered without detection.
  - **Sn4.1.1** `marker_codec` uses HMAC-SHA256 (FIPS 180-4). Any
    byte flip, wrong secret, or stale timestamp raises
    `InvalidMarker`. Four rejection tests in `test_phase9e.py`.

- **G4.2** CRDT merges cannot corrupt peer state.
  - **Sn4.2.1** Merges are commutative + idempotent by construction
    (OR-set + LWW + G-counter). Property-based tests in
    `test_crdt_graph.py` shuffle merge orders and check
    equivalence.

- **G4.3** Ingested external adapter data is typed and validated.
  - **Sn4.3.1** `Meta2SignatureAdapter`, `InfoMGraphAdapter`,
    `In4nSceneAdapter`, `PhysioNetRecord.load_dict` all define
    strict schemas and raise on shape mismatch. Tested in
    `tests/test_adapters.py`, `tests/test_physionet_adapter.py`.

- **G4.4** Test fixtures never contain real PHI.
  - **Sn4.4.1** All test data is generated by
    `sim/casualty_profiles.py` / `sim/realistic_dataset.py` /
    `PhysioNetRecord.load_dict(fixture)`; no real recordings are
    committed.

---

## G5 — Assurance continuity

**Safety claims do not silently regress between commits.**

### S5 — argue via CI + tests-as-specification

- **G5.1** Every safety-relevant claim is backed by at least one
  test that would fail if the claim regressed.
  - **Sn5.1.1** 487 tests run on every commit via GitHub Actions
    (`.github/workflows/ci.yml`).
  - **Sn5.1.2** Python 3.11 + 3.12 matrix.
  - **Sn5.1.3** `ruff` + `mypy` + `pytest` + smoke-run of
    `full_pipeline_benchmark.py` all gate merges.

- **G5.2** Changes to safety-relevant modules are reviewed.
  - **Sn5.2.1** Branch protection on `main` (policy, not yet
    enforced in-repo).
  - **Sn5.2.2** `CHANGELOG.md` records every phase and every
    safety-relevant fix (e.g. the Larrey-gap closure in Phase 9b).

### Residual limitation

- **J5.R1** Coverage is breadth-first (~120 modules, 487 tests) but
  does not yet include mutation testing. Tracked as **CI-002**.

---

## Summary

The current safety case supports the claim that **triage4 is safe to
run as decision-support in a research / pre-clinical setting with a
qualified operator in the loop**.

The following further claims are **not** yet supported:

- ❌ Autonomous clinical use without a human reviewer.
- ❌ Use on real patients outside an IRB-approved study.
- ❌ SaMD Class III regulatory clearance.
- ❌ Deployment in a connected-device environment without a
  cybersecurity review.

Each red-line claim is explicitly tracked in `RISK_REGISTER.md` and
`ROADMAP.md`.

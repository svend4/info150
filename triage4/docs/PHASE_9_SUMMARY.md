# Phase 9 — summary

One-page recap of the three-part Phase 9 work done on branch
`claude/analyze-documents-structure-Ik1KX` on top of the already-closed
Phases 1–8.

## By the numbers

| Metric | After Phase 8 | After Phase 9d |
|---|---|---|
| Python modules | 104 | **120** |
| Tests | 378 | **459+** |
| Example scripts | 3 | **6** |
| Docs | 5 | **8** (+ API, ONE_PAGER, this summary, CHANGELOG) |
| Critical-miss regressions | 1 documented (Larrey-gap) | **0** (closed and test-locked) |
| DARPA gate coverage | 5 / 5 | **5 + counterfactual + HMT** |
| Runtime external-SDK leaks | 0 | **0** |

## What each sub-phase contributed

### 9a — Innovation pack, part 1 (3 modules)

- **`signatures/remote_vitals.py` — Eulerian video magnification.**
  Stand-off HR / RR extraction from an ordinary RGB camera via
  Butterworth bandpass on spatially pooled luminance. Hands off to the
  existing `VitalsEstimator`. MIT CSAIL pattern, first triage-oriented
  implementation.

- **`autonomy/active_sensing.py` — information-gain planner.**
  Replaces fixed coverage plans. Next observation target is picked by
  `expected_info_gain = uncertainty × priority_weight × novelty`,
  using `EvidenceMemory` to count prior observations. The planner is
  transparent and returns its reasoning.

- **`triage_reasoning/larrey_baseline.py` — 1797 Larrey baseline.**
  Digital reconstruction of Napoleonic-era triage rules. Any modern
  classifier that does worse than 200 years of battlefield-validated
  judgement has no business being deployed. Immediately surfaced a
  real calibration gap in the modern engine (below).

### 9b — Real-data classical calibration (5 modules + one-pager)

- **Mortal-sign override in `score_fusion.py`.** Closes the
  Larrey-gap that 9a surfaced: isolated heavy bleeding now correctly
  forces `immediate` regardless of the fused score. Regression test
  locks the fix in place.
- **`perception/yolo_detector.py` — real person-detector path.**
  `LoopbackYOLODetector` for tests plus `build_ultralytics_detector`
  lazy factory behind an optional dep. No PyTorch at base install.
- **`sim/realistic_dataset.py` — 70-case labelled dataset.** Seven
  scenarios including isolated mortal signs and ambiguous mid-band.
  The calibration substrate.
- **`triage_reasoning/calibration.py` — grid-search calibrator.**
  Minimises `critical_miss_rate`, tie-breaks by `macro_f1`. Runs in
  seconds, produces a `CalibrationResult` you can swap into a
  `RapidTriageEngine`.
- **`integrations/physionet_adapter.py` — WFDB adapter.**
  `load_dict` for in-memory records (tests / notebooks); `load_wfdb`
  lazy-imports the SDK for real PhysioNet archives.
- **`docs/ONE_PAGER.md`** — grant-ready project summary.

### 9c — Innovation pack, part 2 (6 modules)

- **`triage_reasoning/bayesian_twin.py` — `PatientTwinFilter`.**
  200-particle filter over `(priority_band, deterioration_rate)`.
  Produces a posterior distribution, not a point estimate. ESS tracked
  as a sanity signal.
- **`evaluation/counterfactual.py` — retrospective regret.**
  Per-casualty "what if we had assigned priority X instead?" against a
  monotonic outcome model. Mean regret is a single dial for mission
  quality.
- **`triage_temporal/entropy_handoff.py` — entropy-based handoff.**
  Shannon entropy of the priority-observation stream decides when to
  hand a casualty off to a medic — not when enough time has passed.
- **`state_graph/crdt_graph.py` — denied-comms coordination.**
  OR-set + LWW-register + G-counter. Provably commutative merges.
  Three medic tablets converge to identical state without a server.
- **`signatures/acoustic_signature.py` — audio channel.**
  Bandpower-based cough / wheeze / groan detector. Deterministic,
  no ML.
- **`triage_reasoning/llm_grounding.py` — grounded explanation.**
  Prompt builder that surfaces every numeric fact the system already
  decided. `TemplateGroundingBackend` makes this LLM-free by default.
  Any LLM provider (OpenAI / Anthropic / local) plugs in through a
  `LLMBackend` Protocol.

### 9d — Consolidation round 2 (this commit)

- **`examples/full_pipeline_benchmark.py` extended** with Bayesian
  twin posteriors, Eulerian stand-off HR, counterfactual replay, and
  grounded explanations. Optional `--json` emits a machine-readable
  scorecard for CI diffing.
- **New example scripts:**
  `examples/bayesian_twin_demo.py`,
  `examples/crdt_sync_demo.py`,
  `examples/counterfactual_replay.py`.
- **`docs/API.md` refreshed** with every Phase 9 public symbol.
- **`docs/ONE_PAGER.md` refreshed** with the new DARPA-plus scorecard
  and the five new technical differentiators.
- **`docs/PHASE_9_SUMMARY.md`** — this document.

## Scorecard snapshot (deterministic, 8 casualties)

```
Gate 1 — find & locate           precision=1.00  recall=1.00  F1=1.00
Gate 2 — rapid triage            accuracy=1.00  critical-miss=0%
Gate 3 — trauma                  macro-F1=0.60  micro-F1=0.57
Gate 4 — vitals (contact)        HR MAE=1.9 bpm  hit@±10=100%
Gate 4 — vitals (Eulerian)       HR MAE=1.9 bpm  max err=3 bpm
HMT lane                         agreement=1.00  timeliness=100%
Counterfactual replay            mean regret=0.062
Bayesian twin (per casualty)     P(true priority) ≥ 0.80 on all 8
```

## What's next (roadmap summary)

| Phase | Status | Notes |
|---|---|---|
| 9a | ✅ done | Eulerian + active sensing + Larrey |
| 9b | ✅ done | Larrey-gap closed, YOLO adapter, calibrator |
| 9c | ✅ done | Bayesian twin + counterfactual + CRDT + acoustic + LLM grounding |
| 9d | ✅ done | Consolidation round 2 |
| 9e | planned | Speculative trio (markers / C.elegans / fractal-mission) |
| 10 | needs HW | Live UAV / quadruped / camera integration |
| 11 | needs partner | Clinical data partnership + IRB |
| 12 | planned | Regulatory awareness docs (SaMD / IEC 62304) |
| 13 | needs customer | Production deployment patterns |

See `docs/ROADMAP.md` for the concrete step-by-step breakdown.

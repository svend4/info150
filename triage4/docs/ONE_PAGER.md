# triage4 — One-Pager

**Autonomous stand-off triage for DARPA-class medical robotics.**

## The problem

Mass-casualty incidents and denied-access battlefields share one
bottleneck: *too few medics, too many casualties, decisions needed in
minutes.* A drone or ground robot can look at every casualty long
before any medic arrives — but without an integrated pipeline for
finding them, scoring urgency, and passing the result to the right
human in time, the data is wasted.

## What triage4 is

A **simulation-first, open-source Python 3.11+ stack** that takes
remote sensor observations, turns them into an auditable triage
decision, and packages it for handoff to a medic.

- 104 modules · 428 tests · CI gated on ruff / mypy / pytest + smoke
  run of the end-to-end benchmark
- Pure numpy / scipy runtime. No GPU required to boot the pipeline.
- No upstream-repo or external-SDK imports at load time — proved in CI.

## DARPA Triage Challenge Event 3 coverage

| Gate | Module | Current synthetic score |
|---|---|---|
| 1 — find & locate | `evaluation/gate1_find_locate` | F1 = 1.00, mean error 0.7 m |
| 2 — rapid triage | `evaluation/gate2_rapid_triage` | accuracy = 1.00, critical-miss = 0% |
| 3 — trauma | `evaluation/gate3_trauma` | micro-F1 = 0.57, macro = 0.60 |
| 4 — vitals (contact) | `evaluation/gate4_vitals` | HR MAE 1.9 bpm, RR MAE 1.9 bpm |
| 4 — vitals (stand-off Eulerian) | `signatures/remote_vitals` | HR MAE 1.9 bpm, max err 3 bpm |
| HMT lane | `evaluation/hmt_lane` | agreement = 1.00, timeliness = 1.00 |
| Counterfactual replay | `evaluation/counterfactual` | mean regret = 0.06 on synthetic |
| Bayesian twin posterior | `triage_reasoning/bayesian_twin` | P(true priority) ≥ 0.80 on all 8 casualties |

All numbers are from a deterministic 8-casualty synthetic benchmark,
reproducible with `python examples/full_pipeline_benchmark.py`
(`--json` for machine-readable output).

## Technical differentiators

- **Fractal K3 architecture** — three orthogonal axes (signal, map,
  dynamics) replicated at three scales (body, meaning, mission),
  giving clean extension points instead of flat layering.
- **Explainability built in** — every triage decision carries a
  reason list plus per-channel confidence. No black-box outputs.
- **Mortal-sign override** — the weighted-fusion score is bypassed
  when any single channel crosses a clinical-risk threshold,
  reproducing the 1797 Larrey decision principle (validated as a
  regression test against the live engine).
- **Cross-domain adapted math** — box-counting / Richardson /
  Curvature Scale Space / DTW / rotation-aware DTW / Fourier shape
  descriptors / Hu moments, all triage-specialised.
- **Radar signatures** — 7-axis heptagram, 8-axis octagram, Q6
  hypercube 6-bit fingerprints for compact categorical clustering.
- **Eulerian video magnification** — stand-off vitals from an ordinary
  RGB camera, no thermal or contact sensor needed.
- **Information-gain active sensing** — autonomy layer picks the next
  observation by expected uncertainty reduction, not by a fixed
  coverage plan.
- **Bayesian patient twin** — particle filter per casualty returns a
  full posterior over priority bands, not a point estimate; effective
  sample size flags degenerate estimates as untrustworthy.
- **Retrospective counterfactual scoring** — every mission can be
  replayed as "what if we'd decided differently?" with per-casualty
  regret scores against a monotonic outcome model.
- **CRDT denied-comms coordination** — three medic tablets syncing
  pairwise over Bluetooth or LoRa converge to identical state without
  a central server. Merges are provably commutative and idempotent.
- **LLM grounding, not LLM decision** — any LLM plug-in only
  *phrases* the numeric facts triage4 already decided. Cannot invent
  clinical claims; the default backend is LLM-free.

## Honest gaps

Alpha / TRL 3–4. Not production-ready. Specifically:

- Real CV perception is a YOLO-class skeleton (loopback simulator
  ships; `ultralytics` backend is lazy-imported and not auto-tested
  in CI).
- No clinical-outcome dataset used yet — thresholds calibrated on a
  70-casualty synthetic set with edge cases and sensor-degradation
  noise.
- Platform bridges (ROS2 / MAVLink / bosdyn) work fully in loopback;
  real-backend wiring is a clearly-marked skeleton.
- No regulatory pathway started — system is framed as **decision
  support**, never a clinical device, and tests assert this framing.

## Roadmap at a glance

- ✅ Phase 1–8: scaffold, signatures, triage, graph, autonomy,
  upstream integration, DARPA gate evaluators, platform bridges
- ✅ Phase 9a: innovation pack 1 — Eulerian magnification, active
  sensing, Larrey baseline
- ✅ Phase 9b: real-data-ready — YOLO adapter, PhysioNet adapter,
  70-case realistic synthetic dataset, threshold calibrator, critical
  Larrey-gap closed
- ⏳ Phase 9c: innovation pack 2 — CRDT denied-comms, Bayesian patient
  twin, counterfactual re-scoring, bioacoustic fusion, steganographic
  markers, C.elegans-topology classifier, entropy handoff, LLM
  grounding
- ⏳ Phase 10: live hardware integration (one real UAV + one real
  sensor chain), clinical validation with a partner, IRB pathway.

## Ask

- **Grant / R&D lab partnership** — land one real sensor stream and
  one clinical-outcome dataset; that's the gate between Alpha and
  credible Beta.
- **Compute / data access** — PhysioNet clinical datasets (MIMIC,
  BIDMC) under an academic agreement; ISIC or equivalent wound
  imagery with pixel-level ground truth.
- **Platform partner** — a physical quadruped or UAV to wire up one
  of the already-sketched platform bridges. The code contract is
  ready; the wiring is ~2 engineer-weeks per platform.

## Contact / next step

Running the full pipeline takes one command:

```bash
pip install -e '.[dev]'
python examples/full_pipeline_benchmark.py
```

Readable scorecard, ~1 second runtime, fully deterministic.

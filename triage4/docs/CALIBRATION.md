# triage4 — Calibration

How to tune `RapidTriageEngine` against a labelled dataset. Built
around the Phase 9b calibrator (`triage_reasoning/calibration.py`)
and the 70-case realistic dataset (`sim/realistic_dataset.py`).

**Framing.** Calibration here means choosing fusion weights and
priority-band thresholds that minimise critical-miss rate first,
then maximise macro-F1 — not adapting or retraining anything
online. The result is a **locked-algorithm** configuration, which
matches the regulatory posture in `REGULATORY.md §7`.

## 1. What gets calibrated

The engine has two knobs:

1. **Fusion weights** — per-channel multipliers that combine
   `bleeding / chest_motion / perfusion / posture` into a single
   urgency score.
2. **Priority-band thresholds** — `immediate_threshold` and
   `delayed_threshold` that map the score to one of the three
   bands (`immediate` > `immediate_threshold` > `delayed` >
   `delayed_threshold` > `minimal`).

`MortalThresholds` (in `score_fusion.py`) is **not** part of
calibration. The mortal-sign override is a clinical safety net —
a calibrator that learned to raise those thresholds would increase
critical-miss rate, which the search criterion forbids.

## 2. Dataset

`sim.realistic_dataset.generate_labelled_dataset` produces a
70-case dataset across 7 scenarios × 10 cases each:

| Scenario | Expected priority | What it exercises |
|---|---|---|
| `clean_immediate` | immediate | prototypical critical |
| `clean_delayed`   | delayed   | prototypical moderate |
| `clean_minimal`   | minimal   | prototypical asymptomatic |
| `isolated_bleeding` | immediate | Larrey mortal-sign case |
| `isolated_no_breathing` | immediate | Larrey mortal-sign case |
| `isolated_collapsed` | immediate | posture-only mortal-sign case |
| `ambiguous_mid` | delayed | weights-sensitive boundary |

A `SensorDegradationSimulator` (light noise + visibility drop) is
applied by default so the calibrator sees non-trivial variance.

## 3. End-to-end walkthrough

```bash
python examples/calibration_walkthrough.py
```

What the script does:

1. Generates the 70-case dataset (`seed=42`, deterministic).
2. Scores the default engine on it — the **baseline**.
3. Runs `calibrate(cases)` — a grid search over weights + thresholds.
4. Builds a new engine from the winning config.
5. Re-scores on the same dataset — the **calibrated** row.
6. Prints a baseline-vs-calibrated delta table.

Typical output on the current codebase:

```
metric                     baseline   calibrated      delta
accuracy                      0.929        0.986 +    0.057
macro-F1                      0.536        0.588 +    0.052
critical miss rate            0.025        0.025 +    0.000
```

The critical-miss rate does not regress — the search objective
guarantees that by construction.

## 4. API

```python
from triage4.sim.realistic_dataset import generate_labelled_dataset
from triage4.triage_reasoning import (
    RapidTriageEngine,
    calibrate,
    build_engine_from_result,
    evaluate_engine_on_dataset,
)

cases = generate_labelled_dataset(n_per_scenario=10, seed=42)

baseline = evaluate_engine_on_dataset(RapidTriageEngine(), cases)
best = calibrate(cases)
calibrated = evaluate_engine_on_dataset(build_engine_from_result(best), cases)
```

`CalibrationResult` carries the chosen `weights`, `immediate_threshold`,
`delayed_threshold`, and the three metrics (`accuracy`, `macro_f1`,
`critical_miss_rate`) for the winning config.

## 5. Search scope

Defaults:

- **Weight grid** — `_default_weight_grid()` walks ~30% around the
  shipped defaults on four channels. Small (a few dozen points)
  for sub-second runs.
- **`immediate_thresholds`** — `[0.55, 0.60, 0.65, 0.70]`.
- **`delayed_thresholds`** — `[0.25, 0.30, 0.35, 0.40]`.
- **Constraint** — `immediate_threshold > delayed_threshold`.

Override any of them to widen the search:

```python
best = calibrate(
    cases,
    weight_grid=my_custom_grid,
    immediate_thresholds=[0.50, 0.55, 0.60, 0.65, 0.70, 0.75],
)
```

Wider grids cost more — full run is still seconds, not minutes.

## 6. When to recalibrate

- **Sensor hardware changes.** New camera → new noise profile →
  retune.
- **Population shift.** If the deployed site has a different
  casualty profile (e.g. more shock cases), synthesise a matching
  dataset and re-run.
- **After a safety-critical code change.** Any edit to
  `score_fusion.py` or `rapid_triage.py` triggers re-calibration
  and regression-tests (`make mutation-quick`).

## 7. Real data

`integrations/physionet_adapter.py` exposes the PhysioNet WFDB
path (`load_wfdb`) and an in-memory `load_dict` for tests. A real
calibration against PhysioNet signals would:

1. Download a dataset under an appropriate agreement (BIDMC,
   MIMIC-III, etc.). See `REGULATORY.md §8` for HIPAA / GDPR
   overlay.
2. Convert each record into a `LabelledCase` via an adapter you
   write — shape matches the in-memory `load_dict` pattern.
3. Feed through `calibrate()` just like the synthetic dataset.

No real PHI ever enters the repo or CI.

## 8. References

- `triage_reasoning/calibration.py` — `calibrate`,
  `CalibrationResult`, `build_engine_from_result`,
  `evaluate_engine_on_dataset`.
- `sim/realistic_dataset.py` — dataset generator.
- `examples/calibration_walkthrough.py` — runnable demo.
- `docs/REGULATORY.md §7` — locked-algorithm vs adaptive-algorithm
  regulatory framing.
- `docs/RISK_REGISTER.md` — CAL-001 / CAL-002 / CAL-003.

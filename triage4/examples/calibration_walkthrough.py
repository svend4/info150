"""triage4 — calibration walkthrough.

End-to-end demonstration of the Phase 9b calibrator:

1. Generate a 70-case realistic dataset from ``sim.realistic_dataset``
   (7 scenarios × 10 cases, with sensor degradation applied).
2. Evaluate the *default* engine on that dataset — establish the
   baseline.
3. Run ``calibrate()`` to grid-search fusion weights and priority
   thresholds that minimise ``critical_miss_rate`` first, then
   maximise ``macro_f1``.
4. Build a calibrated engine and re-evaluate on the same data.
5. Compare baseline vs calibrated side-by-side.

Run from the project root:

    python examples/calibration_walkthrough.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.sim.realistic_dataset import generate_labelled_dataset  # noqa: E402
from triage4.triage_reasoning import (  # noqa: E402
    RapidTriageEngine,
    build_engine_from_result,
    calibrate,
    evaluate_engine_on_dataset,
)


def _hr() -> None:
    print("-" * 70)


def _pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def main() -> None:
    print("triage4 — calibration walkthrough")
    _hr()
    print("[1] generating a realistic 70-case dataset")
    cases = generate_labelled_dataset(n_per_scenario=10, seed=42, apply_degradation=True)
    scenario_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    for c in cases:
        tag = c.casualty_id.rsplit("_", 1)[0]
        scenario_counts[tag] = scenario_counts.get(tag, 0) + 1
        priority_counts[c.priority] = priority_counts.get(c.priority, 0) + 1
    print(f"   total:        {len(cases)} cases")
    print(f"   scenarios:    {scenario_counts}")
    print(f"   by priority:  {priority_counts}")

    _hr()
    print("[2] baseline evaluation (default engine)")
    baseline_engine = RapidTriageEngine()
    baseline = evaluate_engine_on_dataset(baseline_engine, cases)
    print(
        f"   accuracy = {_pct(baseline.accuracy)}   "
        f"macro-F1 = {baseline.macro_f1:.3f}   "
        f"critical miss = {_pct(baseline.critical_miss_rate)}"
    )

    _hr()
    print("[3] running grid-search calibration — a few seconds")
    best = calibrate(cases)
    print(
        f"   chosen weights:  "
        f"bleeding={best.weights.get('bleeding', 0):.2f} "
        f"chest_motion={best.weights.get('chest_motion', 0):.2f} "
        f"perfusion={best.weights.get('perfusion', 0):.2f} "
        f"posture={best.weights.get('posture', 0):.2f}"
    )
    print(
        f"   chosen thresholds: "
        f"immediate ≥ {best.immediate_threshold}   "
        f"delayed ≥ {best.delayed_threshold}"
    )

    _hr()
    print("[4] evaluating calibrated engine")
    calibrated_engine = build_engine_from_result(best)
    calibrated = evaluate_engine_on_dataset(calibrated_engine, cases)
    print(
        f"   accuracy = {_pct(calibrated.accuracy)}   "
        f"macro-F1 = {calibrated.macro_f1:.3f}   "
        f"critical miss = {_pct(calibrated.critical_miss_rate)}"
    )

    _hr()
    print("[5] comparison")
    print(f"{'metric':<22s} {'baseline':>12s} {'calibrated':>12s} {'delta':>10s}")
    for label, b, c in (
        ("accuracy",           baseline.accuracy, calibrated.accuracy),
        ("macro-F1",           baseline.macro_f1, calibrated.macro_f1),
        ("critical miss rate", baseline.critical_miss_rate, calibrated.critical_miss_rate),
    ):
        delta = c - b
        sign = "+" if delta >= 0 else ""
        print(f"{label:<22s} {b:>12.3f} {c:>12.3f} {sign}{delta:>9.3f}")

    _hr()
    if calibrated.critical_miss_rate <= baseline.critical_miss_rate:
        print("✓ calibration did not regress the critical-miss rate.")
    else:
        print("⚠ calibration INCREASED critical-miss rate — investigate before shipping.")


if __name__ == "__main__":
    main()

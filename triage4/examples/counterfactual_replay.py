"""triage4 — retrospective counterfactual replay.

After a mission, takes the actual decisions + eventual outcomes and
asks: *for each casualty, what priority would have maximised the
expected outcome, and how much regret did we accumulate by not
choosing it?*

This is what you'd show a medical director the morning after a
live-fire evaluation — it tells you both where the system shone and
where it could have done better, without touching any patient record.

Run from the project root:

    python examples/counterfactual_replay.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.evaluation import evaluate_counterfactuals  # noqa: E402


# (casualty_id, true_severity, actual_priority, actual_outcome)
MISSION_LOG: list[tuple[str, str, str, float]] = [
    ("C1", "critical", "immediate", 0.80),   # correct
    ("C2", "serious",  "delayed",   0.88),   # correct
    ("C3", "light",    "minimal",   0.97),   # correct
    ("C4", "critical", "delayed",   0.40),   # BIG miss — critical delayed
    ("C5", "light",    "minimal",   0.95),   # correct
    ("C6", "serious",  "minimal",   0.65),   # mild miss
    ("C7", "critical", "immediate", 0.78),   # correct
    ("C8", "light",    "minimal",   0.96),   # correct
]


def _bar(value: float, width: int = 20) -> str:
    full = int(round(value * width))
    return "█" * full + "░" * (width - full)


def main() -> None:
    report = evaluate_counterfactuals(MISSION_LOG, regret_threshold=0.10)
    print("Counterfactual replay")
    print("=" * 60)
    print(
        f"total casualties     : {report.n_total}\n"
        f"cases with regret>0.10 : {report.n_cases_with_regret}\n"
        f"mean regret          : {report.mean_regret:.3f}"
    )
    print()

    print("per-casualty")
    print(f"  {'id':<4s} {'severity':<9s} {'actual':<10s} {'best':<10s} "
          f"{'actual→best'}  regret")
    for case in sorted(report.cases, key=lambda c: -c.regret):
        actual_out = case.actual_outcome
        best_out = case.counterfactuals[case.best_alternative]
        print(
            f"  {case.casualty_id:<4s} {case.true_severity:<9s} "
            f"{case.actual_priority:<10s} {case.best_alternative:<10s} "
            f"{actual_out:.2f}→{best_out:.2f}  "
            f"|{_bar(case.regret)}| {case.regret:.3f}"
        )

    print()
    biggest = max(report.cases, key=lambda c: c.regret)
    if biggest.regret > 0.10:
        print(
            f"biggest regret: {biggest.casualty_id} — "
            f"priority was '{biggest.actual_priority}', should have been "
            f"'{biggest.best_alternative}' "
            f"(gap {biggest.regret:.2f}). Review calibration on "
            f"{biggest.true_severity} casualties."
        )
    else:
        print("no casualty exceeded the regret threshold — mission calibration was adequate.")


if __name__ == "__main__":
    main()

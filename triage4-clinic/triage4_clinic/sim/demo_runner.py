"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..clinic_triage.triage_engine import ClinicalPreTriageEngine
from .synthetic_self_report import demo_submissions


def run_demo() -> str:
    submissions = demo_submissions()
    engine = ClinicalPreTriageEngine()
    lines: list[str] = [
        f"Running {len(submissions)} synthetic submissions "
        "through ClinicalPreTriageEngine.",
        "",
    ]
    for obs in submissions:
        report = engine.review(obs)
        lines.append("=" * 72)
        lines.append(report.as_text())
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

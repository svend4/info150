"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..pet_triage.triage_engine import PetTriageEngine
from .synthetic_submission import demo_submissions


def run_demo() -> str:
    submissions = demo_submissions()
    engine = PetTriageEngine()
    lines: list[str] = [
        f"Running {len(submissions)} synthetic submissions "
        "through PetTriageEngine.",
        "",
    ]
    for obs in submissions:
        report = engine.review(obs)
        a = report.assessment
        lines.append("=" * 70)
        lines.append(
            f"{obs.pet_token}  ({obs.species}, "
            f"age {obs.age_years})  →  {a.recommendation}"
        )
        lines.append(
            f"  channels: gait={a.gait_safety:.2f}  "
            f"resp={a.respiratory_safety:.2f}  "
            f"card={a.cardiac_safety:.2f}  "
            f"pain={a.pain_safety:.2f}  "
            f"overall={a.overall:.2f}"
        )
        lines.append("")
        lines.append("  VET SUMMARY:")
        lines.append(f"    {report.vet_summary.text}")
        lines.append("")
        lines.append("  OWNER MESSAGES:")
        for m in report.owner_messages:
            lines.append(f"    - {m.text}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

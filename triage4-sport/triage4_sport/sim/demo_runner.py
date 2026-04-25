"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..sport_engine.monitoring_engine import SportPerformanceEngine
from .synthetic_session import demo_baseline, demo_sessions


def run_demo() -> str:
    sessions = demo_sessions()
    baseline = demo_baseline()
    engine = SportPerformanceEngine()
    lines: list[str] = [
        f"Running {len(sessions)} synthetic athlete-sessions through "
        "SportPerformanceEngine.",
        "",
    ]
    for obs in sessions:
        report = engine.review(obs, baseline=baseline)
        lines.append("=" * 70)
        lines.append(report.as_text())
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

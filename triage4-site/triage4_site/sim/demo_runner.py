"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..site_monitor.monitoring_engine import SiteSafetyEngine
from .synthetic_shift import demo_shift


def run_demo() -> str:
    obs_list = demo_shift()
    report = SiteSafetyEngine().review(
        site_id="DEMO_SITE", observations=obs_list,
    )
    lines: list[str] = [
        f"Site DEMO_SITE — running {len(obs_list)} worker observations "
        "through SiteSafetyEngine.",
        "",
    ]
    for score in report.scores:
        lines.append(
            f"  {score.worker_token:8s}  level={score.alert_level:8s}  "
            f"overall={score.overall:.2f}  "
            f"ppe={score.ppe_compliance:.2f}  "
            f"lift={score.lifting_safety:.2f}  "
            f"heat={score.heat_safety:.2f}  "
            f"fatigue={score.fatigue_safety:.2f}"
        )
    lines.append("")
    for alert in report.alerts:
        lines.append(
            f"  [{alert.level}/{alert.kind}] {alert.text}"
        )
    lines.extend(["", report.as_text()])
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

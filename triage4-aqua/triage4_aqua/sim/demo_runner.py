"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..pool_watch.monitoring_engine import PoolWatchEngine
from .synthetic_pool import demo_pool


def run_demo() -> str:
    swimmers = demo_pool()
    report = PoolWatchEngine().review(
        pool_id="DEMO_POOL", observations=swimmers,
    )
    lines: list[str] = [
        f"Pool DEMO_POOL — running {len(swimmers)} swimmer observations "
        "through PoolWatchEngine.",
        "",
    ]
    for score in report.scores:
        lines.append(
            f"  {score.swimmer_token:8s}  level={score.alert_level:8s}  "
            f"overall={score.overall:.2f}  "
            f"sub={score.submersion_safety:.2f}  "
            f"idr={score.idr_safety:.2f}  "
            f"abs={score.absent_safety:.2f}  "
            f"dist={score.distress_safety:.2f}"
        )
    lines.append("")
    for alert in report.alerts:
        lines.append(
            f"  [{alert.level}/{alert.kind} @ {alert.swimmer_token}] {alert.text}"
        )
    lines.extend(["", report.as_text()])
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

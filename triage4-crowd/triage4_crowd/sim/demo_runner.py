"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..venue_monitor.monitoring_engine import VenueMonitorEngine
from .synthetic_venue import demo_venue


def run_demo() -> str:
    zones = demo_venue()
    report = VenueMonitorEngine().review(
        venue_id="DEMO_VENUE", zones=zones,
    )
    lines: list[str] = [
        f"Venue DEMO_VENUE — running {len(zones)} zone observations "
        "through VenueMonitorEngine.",
        "",
    ]
    for score in report.scores:
        lines.append(
            f"  {score.zone_id:16s}  level={score.alert_level:8s}  "
            f"overall={score.overall:.2f}  "
            f"dens={score.density_safety:.2f}  "
            f"flow={score.flow_safety:.2f}  "
            f"press={score.pressure_safety:.2f}  "
            f"med={score.medical_safety:.2f}"
        )
    lines.append("")
    for alert in report.alerts:
        lines.append(
            f"  [{alert.level}/{alert.kind} @ {alert.zone_id}] {alert.text}"
        )
    lines.extend(["", report.as_text()])
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

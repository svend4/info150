"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..core.models import HomeReport
from ..home_monitor.monitoring_engine import HomeMonitoringEngine
from .synthetic_day import demo_baseline, demo_day_series


def run_demo() -> str:
    windows = demo_day_series()
    baseline = demo_baseline()
    engine = HomeMonitoringEngine()
    report = HomeReport(residence_id="DEMO_RESIDENCE")

    lines: list[str] = [
        f"Residence DEMO_RESIDENCE — running {len(windows)} "
        "observation windows through HomeMonitoringEngine.",
        "",
    ]
    for obs in windows:
        score, alerts = engine.review(obs, baseline=baseline)
        report.scores.append(score)
        report.alerts.extend(alerts)
        lines.append(
            f"  {obs.window_id:10s}  level={score.alert_level:10s}  "
            f"overall={score.overall:.2f}  "
            f"fall_risk={score.fall_risk:.2f}  "
            f"activity={score.activity_alignment:.2f}  "
            f"mobility={score.mobility_trend:.2f}"
        )
        for a in alerts:
            lines.append(f"      [{a.level}/{a.kind}] {a.text}")

    lines.extend(["", report.as_text()])
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

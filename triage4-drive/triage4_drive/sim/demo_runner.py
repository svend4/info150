"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..core.models import DrivingSession
from ..driver_monitor.monitoring_engine import DriverMonitoringEngine
from .synthetic_cab import demo_session


def run_demo() -> str:
    windows = demo_session(session_id="DEMO_SESSION")
    engine = DriverMonitoringEngine()

    session = DrivingSession(session_id="DEMO_SESSION")
    lines: list[str] = [
        f"Session {session.session_id} — running {len(windows)} "
        "observation windows through DriverMonitoringEngine.",
        "",
    ]
    for obs in windows:
        score, alerts = engine.review(obs)
        session.scores.append(score)
        session.alerts.extend(alerts)
        lines.append(
            f"  {obs.session_id:24s}  level={score.alert_level:8s}  "
            f"overall={score.overall:.2f}  "
            f"PERCLOS={score.perclos:.2f}  "
            f"distraction={score.distraction:.2f}  "
            f"incap={score.incapacitation:.2f}"
        )
        for a in alerts:
            lines.append(f"      [{a.level}/{a.kind}] {a.text}")

    lines.extend(["", session.as_text()])
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

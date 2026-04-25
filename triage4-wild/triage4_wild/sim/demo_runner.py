"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..core.models import ReserveReport
from ..wildlife_health.monitoring_engine import WildlifeHealthEngine
from .synthetic_reserve import demo_observations


def run_demo() -> str:
    obs_list = demo_observations()
    engine = WildlifeHealthEngine()
    aggregate = ReserveReport(reserve_id="DEMO_RESERVE")

    lines: list[str] = [
        f"Reserve DEMO_RESERVE — running {len(obs_list)} "
        "observations through WildlifeHealthEngine.",
        "",
    ]
    for obs in obs_list:
        report = engine.review(obs, reserve_id="DEMO_RESERVE")
        aggregate.scores.extend(report.scores)
        aggregate.alerts.extend(report.alerts)
        s = report.scores[0]
        lines.append(
            f"  {obs.obs_token} ({obs.species:8s} @ "
            f"{obs.location.handle:14s})  "
            f"level={s.alert_level:6s}  overall={s.overall:.2f}  "
            f"gait={s.gait_safety:.2f}  "
            f"therm={s.thermal_safety:.2f}  "
            f"post={s.postural_safety:.2f}  "
            f"bc={s.body_condition_safety:.2f}  "
            f"threat={s.threat_signal:.2f}"
        )
        for a in report.alerts:
            lines.append(
                f"    [{a.level}/{a.kind} @ {a.location_handle}] "
                f"({len(a.text)} chars) {a.text}"
            )

    lines.extend(["", aggregate.as_text()])
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

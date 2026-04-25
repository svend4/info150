"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..bird_health.monitoring_engine import AvianHealthEngine
from .synthetic_station import demo_observations


def run_demo() -> str:
    obs_list = demo_observations()
    engine = AvianHealthEngine()
    lines: list[str] = [
        f"Running {len(obs_list)} synthetic station observations "
        "through AvianHealthEngine.",
        "",
    ]
    for obs in obs_list:
        report = engine.review(obs)
        s = report.scores[0]
        lines.append(
            f"  {obs.obs_token} ({obs.station_id} @ "
            f"{obs.location_handle:12s})  "
            f"level={s.alert_level:6s}  overall={s.overall:.2f}  "
            f"call={s.call_presence_safety:.2f}  "
            f"distress={s.distress_safety:.2f}  "
            f"vitals={s.vitals_safety:.2f}  "
            f"thermal={s.thermal_safety:.2f}  "
            f"mort={s.mortality_cluster_safety:.2f}"
        )
        for a in report.alerts:
            lines.append(
                f"    [{a.level}/{a.kind} @ {a.location_handle}] "
                f"({len(a.text)} ch) {a.text}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

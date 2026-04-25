"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..core.models import PenReport
from ..pen_health.monitoring_engine import AquacultureHealthEngine
from .synthetic_pen import demo_observations


def run_demo() -> str:
    obs_list = demo_observations()
    engine = AquacultureHealthEngine()
    aggregate = PenReport(farm_id="DEMO_FARM")

    lines: list[str] = [
        f"Farm DEMO_FARM — running {len(obs_list)} pen observations "
        "through AquacultureHealthEngine.",
        "",
    ]
    for obs in obs_list:
        report = engine.review(obs, farm_id="DEMO_FARM")
        aggregate.scores.extend(report.scores)
        aggregate.alerts.extend(report.alerts)
        s = report.scores[0]
        lines.append(
            f"  {obs.pen_id} ({obs.species:8s} @ "
            f"{obs.location_handle:8s} · "
            f"water={obs.water_condition:10s})  "
            f"level={s.welfare_level:6s}  overall={s.overall:.2f}  "
            f"gill={s.gill_rate_safety:.2f}  "
            f"school={s.school_cohesion_safety:.2f}  "
            f"lice={s.sea_lice_safety:.2f}  "
            f"mort={s.mortality_safety:.2f}  "
            f"chem={s.water_chemistry_safety:.2f}"
        )
        for a in report.alerts:
            lines.append(
                f"    [{a.level}/{a.kind} @ {a.location_handle}] {a.text}"
            )

    lines.extend(["", aggregate.as_text()])
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

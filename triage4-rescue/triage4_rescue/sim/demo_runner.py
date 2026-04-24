"""Small runnable demo — entry point for ``make demo``."""

from __future__ import annotations

from ..triage_protocol.protocol_engine import StartProtocolEngine
from .synthetic_incident import demo_incident


def run_demo() -> str:
    casualties = demo_incident(incident_id="DEMO_INCIDENT")
    report = StartProtocolEngine().review(
        incident_id="DEMO_INCIDENT",
        casualties=casualties,
    )
    lines: list[str] = [report.as_text(), ""]
    for a in report.assessments:
        lines.append(
            f"  {a.casualty_id:20s}  tag={a.tag:10s}  "
            f"age_group={a.age_group:10s}  "
            f"{'[flag]' if a.flag_for_secondary_review else ''}"
        )
        lines.append(f"    reasoning: {a.reasoning}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_demo())

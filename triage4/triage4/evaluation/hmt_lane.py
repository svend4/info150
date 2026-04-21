"""Human-machine teaming (HMT) lane.

Not a detection gate — measures how well the autonomous system and the
medic cooperate.

Metrics:
- mean time from detection to medic handoff;
- medic-override rate — fraction of system priorities the medic
  overruled after seeing the casualty;
- agreement rate — fraction of casualties where the final medic
  decision matched the system priority;
- timeliness ratio — fraction of ``immediate`` casualties handed off
  within a deadline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class HMTEvent:
    casualty_id: str
    detected_at: float
    handoff_at: float
    system_priority: str
    medic_decision: str


@dataclass
class HMTReport:
    n_events: int
    mean_time_to_handoff_s: float
    max_time_to_handoff_s: float
    agreement_rate: float
    override_rate: float
    immediate_timeliness_rate: float
    params: dict


def evaluate_hmt_lane(
    events: Sequence[HMTEvent],
    immediate_deadline_s: float = 60.0,
) -> HMTReport:
    """Score a sequence of HMT events.

    Each event carries the detection + handoff timestamps plus both the
    system-proposed priority and the medic's final decision.
    """
    if immediate_deadline_s <= 0:
        raise ValueError(
            f"immediate_deadline_s must be > 0, got {immediate_deadline_s}"
        )

    n = len(events)
    if n == 0:
        return HMTReport(
            n_events=0,
            mean_time_to_handoff_s=0.0,
            max_time_to_handoff_s=0.0,
            agreement_rate=0.0,
            override_rate=0.0,
            immediate_timeliness_rate=0.0,
            params={"immediate_deadline_s": immediate_deadline_s},
        )

    handoff_times = [e.handoff_at - e.detected_at for e in events]
    if any(h < 0 for h in handoff_times):
        raise ValueError("handoff_at must be >= detected_at")

    agreements = sum(1 for e in events if e.medic_decision == e.system_priority)
    overrides = n - agreements

    immediate_events = [e for e in events if e.system_priority == "immediate"]
    if immediate_events:
        in_time = sum(
            1
            for e in immediate_events
            if (e.handoff_at - e.detected_at) <= immediate_deadline_s
        )
        immediate_timeliness = in_time / len(immediate_events)
    else:
        immediate_timeliness = 0.0

    return HMTReport(
        n_events=n,
        mean_time_to_handoff_s=round(sum(handoff_times) / n, 3),
        max_time_to_handoff_s=round(max(handoff_times), 3),
        agreement_rate=round(agreements / n, 3),
        override_rate=round(overrides / n, 3),
        immediate_timeliness_rate=round(immediate_timeliness, 3),
        params={"immediate_deadline_s": immediate_deadline_s},
    )

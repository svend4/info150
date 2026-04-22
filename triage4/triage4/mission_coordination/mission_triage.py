"""Apply RapidTriageEngine reasoning at the mission level (fractal).

Part of Phase 9e (speculative, idea #9). The K3 matrix already has a
fractal flavour (the same "signal → structure → dynamics" triad
repeats at the body, meaning and mission scales). This module carries
the symmetry further: the *mission itself* is treated as a casualty
with five signature channels, and the same weighted-fusion logic used
for one patient decides whether the mission is in trouble, steady, or
winding down.

Five mission channels (all in [0, 1]):
- ``casualty_density`` — fraction of platform capacity already loaded
  with casualties;
- ``immediate_fraction`` — share of casualties flagged ``immediate``;
- ``unresolved_sector_fraction`` — how much of the mission graph still
  has open unresolved regions;
- ``medic_utilisation`` — share of medics currently assigned to a
  casualty (near 1.0 = no slack);
- ``time_budget_burn`` — how far along in the mission window we are.

Output: ``MissionPriority`` ∈ {``escalate``, ``sustain``, ``wind_down``}
with contributions and reasons, analogously to ``RapidTriageEngine``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from triage4.graph.casualty_graph import CasualtyGraph
from triage4.graph.mission_graph import MissionGraph


MissionPriority = Literal["escalate", "sustain", "wind_down"]


@dataclass
class MissionSignature:
    casualty_density: float
    immediate_fraction: float
    unresolved_sector_fraction: float
    medic_utilisation: float
    time_budget_burn: float

    def __post_init__(self) -> None:
        for name, val in (
            ("casualty_density", self.casualty_density),
            ("immediate_fraction", self.immediate_fraction),
            ("unresolved_sector_fraction", self.unresolved_sector_fraction),
            ("medic_utilisation", self.medic_utilisation),
            ("time_budget_burn", self.time_budget_burn),
        ):
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {val}")


@dataclass
class MissionTriageResult:
    priority: MissionPriority
    score: float
    contributions: dict[str, float]
    reasons: list[str]


DEFAULT_MISSION_WEIGHTS: dict[str, float] = {
    "casualty_density": 0.20,
    "immediate_fraction": 0.35,
    "unresolved_sector_fraction": 0.20,
    "medic_utilisation": 0.15,
    "time_budget_burn": 0.10,
}


def compute_mission_signature(
    casualty_graph: CasualtyGraph,
    mission_graph: MissionGraph,
    platform_capacity: int = 10,
    n_medics: int = 3,
    elapsed_minutes: float = 0.0,
    mission_window_minutes: float = 60.0,
) -> MissionSignature:
    """Derive mission-level channels from the existing graph state."""
    if platform_capacity <= 0:
        raise ValueError("platform_capacity must be > 0")
    if n_medics <= 0:
        raise ValueError("n_medics must be > 0")
    if mission_window_minutes <= 0:
        raise ValueError("mission_window_minutes must be > 0")

    nodes = casualty_graph.all_nodes()
    n = len(nodes)

    density = min(1.0, n / platform_capacity)

    immediate_n = sum(1 for x in nodes if x.triage_priority == "immediate")
    immediate_fraction = immediate_n / n if n > 0 else 0.0

    n_unresolved = len(mission_graph.unresolved_regions)
    unresolved_fraction = (
        min(1.0, n_unresolved / max(1, n_unresolved + len(nodes)))
        if n_unresolved > 0
        else 0.0
    )

    medic_utilisation = min(1.0, len(mission_graph.medic_assignments) / n_medics)
    time_burn = min(1.0, max(0.0, elapsed_minutes / mission_window_minutes))

    return MissionSignature(
        casualty_density=round(density, 3),
        immediate_fraction=round(immediate_fraction, 3),
        unresolved_sector_fraction=round(unresolved_fraction, 3),
        medic_utilisation=round(medic_utilisation, 3),
        time_budget_burn=round(time_burn, 3),
    )


def classify_mission(
    mission_sig: MissionSignature,
    weights: dict[str, float] | None = None,
) -> MissionTriageResult:
    """Fuse mission channels into an escalate / sustain / wind_down decision."""
    w = dict(weights or DEFAULT_MISSION_WEIGHTS)
    total_weight = sum(w.values())
    if total_weight <= 0.0:
        raise ValueError("sum of weights must be > 0")

    channels = {
        "casualty_density": mission_sig.casualty_density,
        "immediate_fraction": mission_sig.immediate_fraction,
        "unresolved_sector_fraction": mission_sig.unresolved_sector_fraction,
        "medic_utilisation": mission_sig.medic_utilisation,
        "time_budget_burn": mission_sig.time_budget_burn,
    }

    contributions = {
        k: channels[k] * w.get(k, 0.0) / total_weight for k in channels
    }
    score = sum(contributions.values())
    score = max(0.0, min(1.0, score))

    reasons: list[str] = []
    if mission_sig.immediate_fraction >= 0.5:
        reasons.append("immediate casualties dominate the queue")
    if mission_sig.medic_utilisation >= 0.9:
        reasons.append("medic team saturated")
    if mission_sig.unresolved_sector_fraction >= 0.4:
        reasons.append("large area still unresolved")
    if mission_sig.time_budget_burn >= 0.8:
        reasons.append("mission window nearly exhausted")
    if mission_sig.casualty_density >= 0.85:
        reasons.append("platform capacity saturated")

    priority: MissionPriority
    if score >= 0.60:
        priority = "escalate"
    elif score >= 0.25:
        priority = "sustain"
    else:
        priority = "wind_down"

    return MissionTriageResult(
        priority=priority,
        score=round(score, 3),
        contributions={k: round(v, 3) for k, v in contributions.items()},
        reasons=reasons,
    )


def triage_mission(
    casualty_graph: CasualtyGraph,
    mission_graph: MissionGraph,
    platform_capacity: int = 10,
    n_medics: int = 3,
    elapsed_minutes: float = 0.0,
    mission_window_minutes: float = 60.0,
    weights: dict[str, float] | None = None,
) -> tuple[MissionSignature, MissionTriageResult]:
    """One-call helper: graph state → mission signature → mission priority."""
    sig = compute_mission_signature(
        casualty_graph,
        mission_graph,
        platform_capacity=platform_capacity,
        n_medics=n_medics,
        elapsed_minutes=elapsed_minutes,
        mission_window_minutes=mission_window_minutes,
    )
    result = classify_mission(sig, weights=weights)
    return sig, result

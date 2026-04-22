"""Information-gain-driven active sensing.

Part of Phase 9a (innovation pack, idea #2). Instead of a fixed coverage
plan, this module picks the next observation target so that the
*expected reduction in mission-state uncertainty* is maximised.

Inputs:
- a list of ``CasualtyNode``s currently tracked, with their confidence;
- optional ``EvidenceMemory`` so we know how many observations each
  casualty already has (law of diminishing returns — the N-th
  observation of a casualty is less informative than the first);
- optional "time since last seen" from each node's timestamps.

Output: a ranked list of ``SensingRecommendation``s. The autonomy layer
(`autonomy.mission_controller`, `autonomy.route_planner`) consumes the
top-ranked target as its next waypoint / revisit action.

Scoring heuristic (cheap, transparent, explainable):

    expected_info_gain(i) = uncertainty(i) * priority_weight(i) * novelty(i)

where:
- ``uncertainty(i) = 1 - confidence(i)``
- ``priority_weight(i)`` — domain weight: immediate > delayed > minimal
- ``novelty(i) = 1 / (1 + n_observations_of_i)`` — each extra observation
  halves the remaining information until we stop revisiting that node.

This is a deliberate simplification of proper Bayesian experimental
design; it captures the right *monotonicity* without needing a full
posterior over casualty state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from triage4.core.models import CasualtyNode
from triage4.state_graph.evidence_memory import EvidenceMemory


_PRIORITY_WEIGHT: dict[str, float] = {
    "immediate": 1.0,
    "delayed": 0.6,
    "minimal": 0.3,
    "expectant": 0.2,
    "unknown": 0.8,
}


@dataclass
class SensingRecommendation:
    casualty_id: str
    expected_info_gain: float
    uncertainty: float
    priority_weight: float
    novelty: float
    n_prior_observations: int
    reasons: list[str] = field(default_factory=list)


def _observation_count(memory: EvidenceMemory | None, casualty_id: str) -> int:
    if memory is None:
        return 0
    return len(memory.events_for(casualty_id))


def _score_node(
    node: CasualtyNode,
    memory: EvidenceMemory | None,
    priority_weights: dict[str, float],
) -> SensingRecommendation:
    uncertainty = max(0.0, min(1.0, 1.0 - float(node.confidence)))
    priority_weight = priority_weights.get(node.triage_priority, 0.5)
    n_obs = _observation_count(memory, node.id)
    novelty = 1.0 / (1.0 + float(n_obs))

    gain = uncertainty * priority_weight * novelty

    reasons: list[str] = []
    if uncertainty > 0.5:
        reasons.append(f"high uncertainty ({uncertainty:.2f})")
    if priority_weight >= _PRIORITY_WEIGHT["immediate"]:
        reasons.append("immediate priority")
    if n_obs == 0:
        reasons.append("never observed again after detection")
    elif n_obs >= 3:
        reasons.append(f"already observed {n_obs}× — novelty fading")

    return SensingRecommendation(
        casualty_id=node.id,
        expected_info_gain=round(gain, 4),
        uncertainty=round(uncertainty, 3),
        priority_weight=round(priority_weight, 3),
        novelty=round(novelty, 3),
        n_prior_observations=n_obs,
        reasons=reasons,
    )


class ActiveSensingPlanner:
    """Recommend the next sensing target by expected information gain."""

    def __init__(
        self,
        priority_weights: dict[str, float] | None = None,
    ) -> None:
        self.priority_weights = dict(priority_weights or _PRIORITY_WEIGHT)

    def rank(
        self,
        nodes: list[CasualtyNode],
        memory: Optional[EvidenceMemory] = None,
    ) -> list[SensingRecommendation]:
        ranked = [
            _score_node(n, memory, self.priority_weights) for n in nodes
        ]
        ranked.sort(key=lambda r: r.expected_info_gain, reverse=True)
        return ranked

    def recommend_next(
        self,
        nodes: list[CasualtyNode],
        memory: Optional[EvidenceMemory] = None,
    ) -> SensingRecommendation | None:
        ranked = self.rank(nodes, memory)
        return ranked[0] if ranked else None

    def top_k(
        self,
        nodes: list[CasualtyNode],
        k: int,
        memory: Optional[EvidenceMemory] = None,
    ) -> list[SensingRecommendation]:
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")
        return self.rank(nodes, memory)[:k]

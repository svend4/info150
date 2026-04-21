from __future__ import annotations

from triage4.core.models import CasualtySignature, TraumaHypothesis
from triage4.triage_reasoning.score_fusion import (
    DEFAULT_WEIGHTS,
    fuse_triage_score,
    priority_from_score,
)


class RapidTriageEngine:
    """Rapid triage engine backed by explicit score fusion.

    The engine delegates the numeric part to ``score_fusion.fuse_triage_score``
    (which is built on top of meta2's ``ScoreVector`` / ``weighted_combine``
    primitives). The engine itself just turns the fused score into a triage
    priority and a human-readable reason list.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = dict(weights or DEFAULT_WEIGHTS)

    def infer_priority(
        self, sig: CasualtySignature
    ) -> tuple[str, float, list[str]]:
        combined = fuse_triage_score(sig, self.weights)
        priority = priority_from_score(combined.score)
        reasons = self._reasons(sig, combined.contributions)
        return priority, round(combined.score, 3), reasons

    def build_hypotheses(self, sig: CasualtySignature) -> list[TraumaHypothesis]:
        out: list[TraumaHypothesis] = []

        if sig.bleeding_visual_score > 0.75:
            out.append(
                TraumaHypothesis(
                    kind="hemorrhage",
                    score=sig.bleeding_visual_score,
                    evidence=["bleeding_visual_score"],
                    explanation="high-probability bleeding signature",
                )
            )
        if sig.chest_motion_fd < 0.12:
            out.append(
                TraumaHypothesis(
                    kind="respiratory_distress",
                    score=0.78,
                    evidence=["chest_motion_fd"],
                    explanation="very weak chest motion pattern",
                )
            )
        if sig.perfusion_drop_score > 0.70:
            out.append(
                TraumaHypothesis(
                    kind="shock_risk",
                    score=sig.perfusion_drop_score,
                    evidence=["perfusion_drop_score"],
                    explanation="possible low-perfusion state",
                )
            )
        return out

    @staticmethod
    def _reasons(
        sig: CasualtySignature, contributions: dict[str, float]
    ) -> list[str]:
        reasons: list[str] = []
        if contributions.get("bleeding", 0.0) > 0.1 and sig.bleeding_visual_score > 0.80:
            reasons.append("possible severe hemorrhage")
        if (
            contributions.get("chest_motion", 0.0) > 0.05
            and sig.chest_motion_fd < 0.15
            and len(sig.breathing_curve) >= 4
        ):
            reasons.append("weak chest motion")
        if contributions.get("perfusion", 0.0) > 0.05 and sig.perfusion_drop_score > 0.70:
            reasons.append("poor perfusion pattern")
        if contributions.get("posture", 0.0) > 0.03 and sig.posture_instability_score > 0.70:
            reasons.append("posture collapse")
        return reasons

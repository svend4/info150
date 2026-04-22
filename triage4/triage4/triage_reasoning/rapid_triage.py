from __future__ import annotations

from triage4.core.models import CasualtySignature, TraumaHypothesis
from triage4.triage_reasoning.score_fusion import (
    DEFAULT_WEIGHTS,
    MortalThresholds,
    detect_mortal_signs,
    fuse_triage_score,
    priority_from_score,
)


class RapidTriageEngine:
    """Rapid triage engine backed by explicit score fusion.

    The engine delegates the numeric part to ``score_fusion.fuse_triage_score``
    (which is built on top of meta2's ``ScoreVector`` / ``weighted_combine``
    primitives). The engine turns the fused score into a priority via
    ``priority_from_score`` — which also applies the mortal-sign override
    introduced in Phase 9b (the isolated-heavy-bleeding case originally
    surfaced by the Larrey baseline).
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        mortal_thresholds: MortalThresholds | None = None,
    ) -> None:
        self.weights = dict(weights or DEFAULT_WEIGHTS)
        self.mortal_thresholds = mortal_thresholds or MortalThresholds()

    def infer_priority(
        self, sig: CasualtySignature
    ) -> tuple[str, float, list[str]]:
        combined = fuse_triage_score(sig, self.weights)
        priority = priority_from_score(
            combined.score, sig=sig, thresholds=self.mortal_thresholds
        )
        reasons = self._reasons(sig, combined.contributions)
        # Mortal-sign override surfaces in the reason list so the operator
        # can see why the priority jumped above the fused score.
        mortal = detect_mortal_signs(sig, self.mortal_thresholds)
        if mortal and priority == "immediate" and combined.score < 0.65:
            reasons.append(
                f"mortal-sign override ({', '.join(mortal)})"
            )
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

from __future__ import annotations

from triage4.core.models import CasualtySignature, TraumaHypothesis


class TraumaAssessmentEngine:
    """Deeper trauma hypotheses layered on top of rapid triage."""

    def build_hypotheses(self, sig: CasualtySignature) -> list[TraumaHypothesis]:
        out: list[TraumaHypothesis] = []

        if sig.bleeding_visual_score > 0.75:
            out.append(
                TraumaHypothesis(
                    kind="hemorrhage",
                    score=sig.bleeding_visual_score,
                    evidence=["wound_visual_pattern", "thermal_inconsistency"],
                    explanation="high-probability bleeding signature",
                )
            )

        if sig.chest_motion_fd < 0.12:
            out.append(
                TraumaHypothesis(
                    kind="respiratory_distress",
                    score=0.78,
                    evidence=["low_chest_motion"],
                    explanation="very weak chest motion pattern",
                )
            )

        if sig.perfusion_drop_score > 0.70:
            out.append(
                TraumaHypothesis(
                    kind="shock_risk",
                    score=0.73,
                    evidence=["skin_perfusion_drop"],
                    explanation="possible low-perfusion state",
                )
            )

        if sig.posture_instability_score > 0.70:
            out.append(
                TraumaHypothesis(
                    kind="unresponsive",
                    score=sig.posture_instability_score,
                    evidence=["posture_instability"],
                    explanation="abnormal or collapsed posture pattern",
                )
            )

        return out

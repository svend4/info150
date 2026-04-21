from __future__ import annotations

from triage4.core.models import CasualtySignature, TraumaHypothesis


class RapidTriageEngine:
    """Score-fusion rapid triage.

    Combines bleeding, chest-motion and perfusion cues into an urgency score.
    Returns (priority, score, reasons). Intentionally simple: every decision
    carries an explicit reason list, which is required for decision support.
    """

    def infer_priority(self, sig: CasualtySignature) -> tuple[str, float, list[str]]:
        reasons: list[str] = []
        score = 0.0

        if sig.bleeding_visual_score > 0.80:
            score += 0.45
            reasons.append("possible severe hemorrhage")

        if sig.chest_motion_fd < 0.15 and len(sig.breathing_curve) >= 4:
            score += 0.30
            reasons.append("weak chest motion")

        if sig.perfusion_drop_score > 0.70:
            score += 0.20
            reasons.append("poor perfusion pattern")

        if score >= 0.65:
            return "immediate", score, reasons
        if score >= 0.35:
            return "delayed", score, reasons
        return "minimal", score, reasons

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

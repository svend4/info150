"""Score fusion for a single casualty.

Reuses ``triage4.matching.score_combiner`` (ported from meta2) so that every
triage priority carries explicit per-signal contributions instead of opaque
hard-coded thresholds. This is what the K3-matrix calls the 2.3 Temporal
Triage Reasoning Layer — score-based, explainable, replayable.
"""

from __future__ import annotations

from triage4.core.models import CasualtySignature
from triage4.matching.score_combiner import (
    CombinedScore,
    ScoreVector,
    weighted_combine,
)


DEFAULT_WEIGHTS: dict[str, float] = {
    "bleeding": 0.45,
    "chest_motion": 0.30,
    "perfusion": 0.20,
    "posture": 0.05,
}


def signature_to_score_vector(
    sig: CasualtySignature, casualty_idx: int = 0
) -> ScoreVector:
    """Convert a CasualtySignature into a fusion-ready ScoreVector.

    All component scores are clamped into [0, 1] so ScoreVector's validation
    is always satisfied, even for pathological inputs.
    """
    chest_motion_risk = 1.0 - _clamp01(sig.chest_motion_fd)
    if len(sig.breathing_curve) < 4:
        chest_motion_risk = 0.0

    return ScoreVector(
        idx1=int(casualty_idx),
        idx2=0,
        scores={
            "bleeding": _clamp01(sig.bleeding_visual_score),
            "chest_motion": _clamp01(chest_motion_risk),
            "perfusion": _clamp01(sig.perfusion_drop_score),
            "posture": _clamp01(sig.posture_instability_score),
        },
    )


def fuse_triage_score(
    sig: CasualtySignature,
    weights: dict[str, float] | None = None,
    casualty_idx: int = 0,
) -> CombinedScore:
    """Fuse signature components into one weighted urgency score."""
    sv = signature_to_score_vector(sig, casualty_idx=casualty_idx)
    return weighted_combine(sv, weights or DEFAULT_WEIGHTS)


def priority_from_score(score: float) -> str:
    """Project a [0, 1] urgency score onto triage priority bands."""
    if score >= 0.65:
        return "immediate"
    if score >= 0.35:
        return "delayed"
    return "minimal"


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))

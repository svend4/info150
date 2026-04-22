"""Score fusion for a single casualty.

Reuses ``triage4.matching.score_combiner`` (ported from meta2) so that every
triage priority carries explicit per-signal contributions instead of opaque
hard-coded thresholds. This is what the K3-matrix calls the 2.3 Temporal
Triage Reasoning Layer — score-based, explainable, replayable.

Mortal-sign override (added in Phase 9b): pure score fusion cannot cross
the immediate-threshold from a single channel alone even when that channel
is catastrophic (this was the Larrey-gap surfaced by Phase 9a's baseline
test). If any individual signal exceeds its mortal threshold we force the
priority to ``immediate`` regardless of the fused score.
"""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class MortalThresholds:
    """Per-channel thresholds above which a single signal is by itself
    sufficient to force an ``immediate`` priority.

    Tuned against the Larrey-baseline decision tree: any one of these
    signs is enough for a Napoleonic field surgeon to classify the
    casualty as dangerously wounded.
    """

    bleeding: float = 0.80
    chest_motion_absence: float = 0.05   # chest_motion_fd BELOW this
    perfusion: float = 0.80
    posture: float = 0.80


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


def detect_mortal_signs(
    sig: CasualtySignature,
    thresholds: MortalThresholds | None = None,
) -> list[str]:
    """Return the list of mortal-sign channel names currently triggered."""
    t = thresholds or MortalThresholds()
    signs: list[str] = []

    if sig.bleeding_visual_score >= t.bleeding:
        signs.append("bleeding")
    if (
        sig.chest_motion_fd <= t.chest_motion_absence
        and len(sig.breathing_curve) >= 4
    ):
        signs.append("chest_motion_absence")
    if sig.perfusion_drop_score >= t.perfusion:
        signs.append("perfusion")
    if sig.posture_instability_score >= t.posture:
        signs.append("posture")
    return signs


def priority_from_score(
    score: float,
    sig: CasualtySignature | None = None,
    thresholds: MortalThresholds | None = None,
) -> str:
    """Project a [0, 1] urgency score onto triage priority bands.

    When ``sig`` is supplied, a mortal-sign override kicks in: any single
    channel above its mortal threshold forces ``immediate`` regardless of
    the fused score. This is the Phase 9b fix for the Larrey-gap that was
    documented in ``tests/test_larrey_baseline.py``.
    """
    if sig is not None and detect_mortal_signs(sig, thresholds):
        return "immediate"
    if score >= 0.65:
        return "immediate"
    if score >= 0.35:
        return "delayed"
    return "minimal"


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))

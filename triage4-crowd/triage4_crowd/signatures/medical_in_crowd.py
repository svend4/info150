"""Medical-in-crowd signature.

Anonymous collapsed-person candidates flagged by upstream
pose detection are scored against a confidence-weighted
sum, normalised so the presence of any high-confidence
candidate drives the score low.

The library never infers the clinical cause — a collapsed-
person candidate might be a medical emergency, a fall,
someone sleeping, a child sitting low. The scoring layer
flags the need for human medic review; no diagnosis is
emitted.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import MedicalCandidate


# Per-candidate weighting bands. Below ``low`` the candidate
# is treated as a possible false-positive; above ``high`` it
# contributes full weight to the safety drop.
_LOW_CONFIDENCE = 0.4
_HIGH_CONFIDENCE = 0.75


def compute_medical_safety(
    candidates: Iterable[MedicalCandidate],
) -> float:
    """Return medical-in-crowd safety score in [0, 1].

    No candidates → 1.0. A single high-confidence candidate
    drops the score to ~0.0; several medium-confidence
    candidates accumulate to drive it down.
    """
    candidate_list = list(candidates)
    if not candidate_list:
        return 1.0

    total_weight = 0.0
    for c in candidate_list:
        if c.confidence < _LOW_CONFIDENCE:
            continue
        if c.confidence >= _HIGH_CONFIDENCE:
            weight = 1.0
        else:
            span = _HIGH_CONFIDENCE - _LOW_CONFIDENCE
            weight = (c.confidence - _LOW_CONFIDENCE) / span
        total_weight += weight

    # Any single high-confidence candidate is already > 0.9
    # in weight, which drives safety to 0.1 (urgent band).
    safety = 1.0 - min(1.0, total_weight)
    return max(0.0, min(1.0, safety))

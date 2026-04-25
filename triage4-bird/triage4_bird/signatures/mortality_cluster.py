"""Mortality-cluster signature.

Counts confidence-weighted dead-bird candidates within
the observation window. A high count is the mortality-
cluster surveillance signal — surfaced as a CANDIDATE,
never as a confirmed outbreak (see surveillance-overreach
boundary in docs/PHILOSOPHY.md).
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import DeadBirdCandidate


_MIN_CONFIDENCE = 0.5
_HIGH_COUNT = 5.0  # weighted-count above which safety → 0


def compute_mortality_cluster_safety(
    candidates: Iterable[DeadBirdCandidate],
) -> float:
    """Return mortality-cluster safety score in [0, 1].

    1.0 = no candidates above the confidence floor.
    0.0 = sufficient candidates that the consumer app
    should trigger the sampling workflow.
    """
    candidate_list = [
        c for c in candidates if c.confidence >= _MIN_CONFIDENCE
    ]
    if not candidate_list:
        return 1.0

    weighted_count = sum(c.confidence for c in candidate_list)
    if weighted_count >= _HIGH_COUNT:
        return 0.0
    return max(0.0, min(1.0, 1.0 - weighted_count / _HIGH_COUNT))

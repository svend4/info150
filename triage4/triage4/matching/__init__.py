"""Matching and score-fusion primitives.

Ported from svend4/meta2 ``puzzle_reconstruction/matching``:
- ``dtw`` — Dynamic Time Warping for comparing temporal triage signals
- ``score_combiner`` — ScoreVector / CombinedScore fusion utilities
- ``matcher_registry`` — name-based registry of matcher functions

These primitives back ``triage4.triage_reasoning.score_fusion``.
"""

from .dtw import dtw_distance, dtw_distance_mirror
from .matcher_registry import (
    MATCHER_REGISTRY,
    compute_scores,
    get_matcher,
    list_matchers,
    register,
    register_fn,
)
from .score_combiner import (
    CombinedScore,
    ScoreVector,
    batch_combine,
    max_combine,
    min_combine,
    normalize_score_vectors,
    rank_combine,
    weighted_combine,
)

__all__ = [
    "CombinedScore",
    "MATCHER_REGISTRY",
    "ScoreVector",
    "batch_combine",
    "compute_scores",
    "dtw_distance",
    "dtw_distance_mirror",
    "get_matcher",
    "list_matchers",
    "max_combine",
    "min_combine",
    "normalize_score_vectors",
    "rank_combine",
    "register",
    "register_fn",
    "weighted_combine",
]

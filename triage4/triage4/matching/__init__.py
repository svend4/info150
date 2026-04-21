"""Matching and score-fusion primitives.

Ported from svend4/meta2 ``puzzle_reconstruction/matching``:
- ``dtw`` — Dynamic Time Warping for comparing temporal triage signals
- ``score_combiner`` — ScoreVector / CombinedScore fusion utilities
- ``matcher_registry`` — name-based registry of matcher functions

These primitives back ``triage4.triage_reasoning.score_fusion``.
"""

from .boundary_matcher import (
    BoundaryMatch,
    batch_match_boundaries,
    chamfer_distance,
    extract_boundary_points,
    frechet_approx,
    hausdorff_distance,
    match_boundary_pair,
    score_boundary_pair,
)
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
from .shape_match import ShapeMatch, shape_distances, shape_similarity

__all__ = [
    "BoundaryMatch",
    "CombinedScore",
    "MATCHER_REGISTRY",
    "ScoreVector",
    "ShapeMatch",
    "batch_combine",
    "batch_match_boundaries",
    "chamfer_distance",
    "compute_scores",
    "dtw_distance",
    "dtw_distance_mirror",
    "extract_boundary_points",
    "frechet_approx",
    "get_matcher",
    "hausdorff_distance",
    "list_matchers",
    "match_boundary_pair",
    "max_combine",
    "min_combine",
    "normalize_score_vectors",
    "rank_combine",
    "register",
    "register_fn",
    "score_boundary_pair",
    "shape_distances",
    "shape_similarity",
    "weighted_combine",
]

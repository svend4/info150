"""Matching and score-fusion primitives.

Ported from svend4/meta2 ``puzzle_reconstruction/matching``:
- ``dtw`` — Dynamic Time Warping for comparing temporal triage signals
- ``score_combiner`` — ScoreVector / CombinedScore fusion utilities
- ``matcher_registry`` — name-based registry of matcher functions
- ``boundary_matcher`` — Hausdorff / Chamfer / Fréchet shape metrics
- ``candidate_ranker`` — CandidatePair ranking and dedup
- ``score_normalizer`` — min-max / z-score / rank normalization
- ``geometric_match`` — area / aspect / Hu-moment shape matching

These primitives back ``triage4.triage_reasoning.score_fusion``.
"""

from .geometric_match import (
    FragmentGeometry,
    GeometricMatchResult,
    area_ratio_similarity,
    aspect_ratio_similarity,
    batch_geometry_match,
    compute_geometry_from_contour,
    edge_length_similarity,
    hu_moments_similarity,
    match_geometry,
)
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
from .candidate_ranker import (
    CandidatePair,
    batch_rank,
    deduplicate_pairs,
    filter_by_score,
    rank_pairs,
    score_pair,
    top_k,
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
from .score_normalizer import (
    ScoreNormResult,
    batch_normalize_scores,
    calibrate_scores,
    combine_scores,
    normalize_minmax,
    normalize_rank,
    normalize_score_matrix,
    normalize_zscore,
)
from .shape_match import ShapeMatch, shape_distances, shape_similarity

__all__ = [
    "BoundaryMatch",
    "CandidatePair",
    "CombinedScore",
    "FragmentGeometry",
    "GeometricMatchResult",
    "MATCHER_REGISTRY",
    "ScoreNormResult",
    "ScoreVector",
    "ShapeMatch",
    "area_ratio_similarity",
    "aspect_ratio_similarity",
    "batch_combine",
    "batch_geometry_match",
    "compute_geometry_from_contour",
    "edge_length_similarity",
    "hu_moments_similarity",
    "match_geometry",
    "batch_match_boundaries",
    "batch_normalize_scores",
    "batch_rank",
    "calibrate_scores",
    "chamfer_distance",
    "combine_scores",
    "compute_scores",
    "deduplicate_pairs",
    "dtw_distance",
    "dtw_distance_mirror",
    "extract_boundary_points",
    "filter_by_score",
    "frechet_approx",
    "get_matcher",
    "hausdorff_distance",
    "list_matchers",
    "match_boundary_pair",
    "max_combine",
    "min_combine",
    "normalize_minmax",
    "normalize_rank",
    "normalize_score_matrix",
    "normalize_score_vectors",
    "normalize_zscore",
    "rank_combine",
    "rank_pairs",
    "register",
    "register_fn",
    "score_boundary_pair",
    "score_pair",
    "shape_distances",
    "shape_similarity",
    "top_k",
    "weighted_combine",
]

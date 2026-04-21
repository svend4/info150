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

from .curve_descriptor import (
    CurveDescriptor,
    CurveDescriptorConfig,
    batch_describe_curves,
    compute_curvature_profile,
    compute_fourier_descriptor,
    describe_curve,
    descriptor_distance,
    descriptor_similarity,
    find_best_match,
)
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
from .pair_scorer import (
    PairScoreResult,
    ScoringWeights,
    aggregate_channels,
    batch_score_pairs,
    build_score_matrix,
    select_top_pairs,
)
from .pair_scorer import score_pair as score_pair_channels
from .affine_matcher import (
    AffineMatchResult,
    affine_reprojection_error,
    apply_affine_pts,
    estimate_affine,
    match_points_affine,
    score_affine_match,
)
from .rotation_dtw import (
    RotationDTWResult,
    batch_rotation_dtw,
    rotation_dtw,
    rotation_dtw_similarity,
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
    "AffineMatchResult",
    "BoundaryMatch",
    "CandidatePair",
    "CombinedScore",
    "CurveDescriptor",
    "CurveDescriptorConfig",
    "FragmentGeometry",
    "GeometricMatchResult",
    "MATCHER_REGISTRY",
    "PairScoreResult",
    "RotationDTWResult",
    "ScoreNormResult",
    "ScoreVector",
    "ScoringWeights",
    "ShapeMatch",
    "affine_reprojection_error",
    "aggregate_channels",
    "apply_affine_pts",
    "area_ratio_similarity",
    "aspect_ratio_similarity",
    "batch_combine",
    "batch_describe_curves",
    "batch_geometry_match",
    "batch_score_pairs",
    "build_score_matrix",
    "compute_curvature_profile",
    "compute_fourier_descriptor",
    "compute_geometry_from_contour",
    "describe_curve",
    "descriptor_distance",
    "descriptor_similarity",
    "edge_length_similarity",
    "estimate_affine",
    "find_best_match",
    "hu_moments_similarity",
    "match_geometry",
    "score_pair_channels",
    "select_top_pairs",
    "batch_match_boundaries",
    "batch_normalize_scores",
    "batch_rank",
    "batch_rotation_dtw",
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
    "match_points_affine",
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
    "rotation_dtw",
    "rotation_dtw_similarity",
    "score_affine_match",
    "score_boundary_pair",
    "score_pair",
    "shape_distances",
    "shape_similarity",
    "top_k",
    "weighted_combine",
]

"""Score-level utilities ported from ``svend4/meta2/puzzle_reconstruction/scoring``.

This subpackage complements ``triage4.matching``: where matching handles
pairwise distances and fusion, scoring handles thresholding, evidence
aggregation, rank-list fusion and global ranking across a whole batch of
scored entities.
"""

from .evidence_aggregator import (
    EvidenceConfig,
    EvidenceScore,
    aggregate_evidence,
    batch_aggregate,
    compute_confidence,
    rank_by_evidence,
    threshold_evidence,
    weight_evidence,
)
from .pair_ranker import (
    RankConfig,
    RankResult,
    RankedPair,
    build_rank_matrix,
    compute_pair_score,
    merge_rank_results,
)
from .pair_ranker import rank_pairs as rank_pairs_detailed
from .consistency_checker import (
    ConsistencyIssue,
    ConsistencyReport,
    batch_consistency_check,
    check_all_present,
    check_canvas_bounds,
    check_gap_uniformity,
    check_score_threshold,
    check_unique_ids,
    run_consistency_check,
)
from .rank_fusion import (
    borda_count,
    fuse_rankings,
    normalize_scores,
    reciprocal_rank_fusion,
    score_fusion,
)
from .threshold_selector import (
    ThresholdConfig,
    ThresholdResult,
    apply_threshold,
    batch_select_thresholds,
    select_adaptive_threshold,
    select_f1_threshold,
    select_fixed_threshold,
    select_otsu_threshold,
    select_percentile_threshold,
    select_threshold,
)

__all__ = [
    "ConsistencyIssue",
    "ConsistencyReport",
    "EvidenceConfig",
    "EvidenceScore",
    "RankConfig",
    "RankResult",
    "RankedPair",
    "ThresholdConfig",
    "ThresholdResult",
    "aggregate_evidence",
    "apply_threshold",
    "batch_aggregate",
    "batch_consistency_check",
    "batch_select_thresholds",
    "borda_count",
    "build_rank_matrix",
    "check_all_present",
    "check_canvas_bounds",
    "check_gap_uniformity",
    "check_score_threshold",
    "check_unique_ids",
    "compute_confidence",
    "compute_pair_score",
    "fuse_rankings",
    "merge_rank_results",
    "normalize_scores",
    "rank_by_evidence",
    "rank_pairs_detailed",
    "reciprocal_rank_fusion",
    "run_consistency_check",
    "score_fusion",
    "select_adaptive_threshold",
    "select_f1_threshold",
    "select_fixed_threshold",
    "select_otsu_threshold",
    "select_percentile_threshold",
    "select_threshold",
    "threshold_evidence",
    "weight_evidence",
]

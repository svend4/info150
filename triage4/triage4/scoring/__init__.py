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
    "EvidenceConfig",
    "EvidenceScore",
    "ThresholdConfig",
    "ThresholdResult",
    "aggregate_evidence",
    "apply_threshold",
    "batch_aggregate",
    "batch_select_thresholds",
    "borda_count",
    "compute_confidence",
    "fuse_rankings",
    "normalize_scores",
    "rank_by_evidence",
    "reciprocal_rank_fusion",
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

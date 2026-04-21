"""Score-level utilities ported from ``svend4/meta2/puzzle_reconstruction/scoring``.

This subpackage complements ``triage4.matching``: where matching handles
pairwise distances and fusion, scoring handles thresholding, global
ranking and aggregation across a whole batch of scored entities.
"""

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
    "ThresholdConfig",
    "ThresholdResult",
    "apply_threshold",
    "batch_select_thresholds",
    "select_adaptive_threshold",
    "select_f1_threshold",
    "select_fixed_threshold",
    "select_otsu_threshold",
    "select_percentile_threshold",
    "select_threshold",
]

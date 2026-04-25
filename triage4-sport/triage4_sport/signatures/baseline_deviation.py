"""Baseline-deviation aggregator.

Convenience signature that combines the per-channel
deviations into a single fused score, surfaced as its own
channel so the engine can decide whether to escalate to
PhysicianAlert (sustained multi-channel deviation crosses
that bar; single-channel deviations don't).
"""

from __future__ import annotations


SIGNATURE_VERSION = "baseline_deviation@1.0.0"


def compute_baseline_deviation_safety(
    form_safety: float,
    workload_safety: float,
    recovery_safety: float,
) -> float:
    """Combine per-channel safety scores into an overall
    baseline-deviation score.

    Returns 1.0 when all channels are at or near 1.0; lower
    when multiple channels are simultaneously deviated
    (multiplicative penalty — single-channel deviations
    barely move the score, multi-channel deviations
    compound).
    """
    # Geometric-mean-style combination — multi-channel
    # deviation compounds.
    combined = (form_safety * workload_safety * recovery_safety) ** (1.0 / 3.0)
    return max(0.0, min(1.0, combined))

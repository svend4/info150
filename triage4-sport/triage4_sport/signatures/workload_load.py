"""Workload-load signature.

Acute-load proxy from one session's GPS-vest aggregates,
compared to the athlete's chronic baseline. Inspired by the
acute:chronic workload ratio (ACWR) concept from sports-
medicine literature (Gabbett 2016 onward), simplified for a
per-session input.

Returns a unit-interval safety score; 1.0 = workload near
or below typical baseline, 0.0 = sharp acute spike well
above baseline.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import WorkloadSample


SIGNATURE_VERSION = "workload_load@1.0.0"


def _normalised_workload(sample: WorkloadSample) -> float:
    """Combine the GPS-vest fields into a [0, 1] index.

    Distances above 12 km / sessions with >150 sprints are
    'high-load' sessions in elite-soccer literature; we
    saturate beyond those thresholds.
    """
    dist_factor = min(1.0, sample.distance_m / 12000.0)
    sprints_factor = min(1.0, sample.high_speed_runs / 150.0)
    accel_factor = min(1.0, sample.accelerations / 200.0)
    decel_factor = min(1.0, sample.decelerations / 200.0)
    # Weighted mean — distance + sprints carry more weight
    # than raw accel counts.
    return (
        0.35 * dist_factor
        + 0.30 * sprints_factor
        + 0.175 * accel_factor
        + 0.175 * decel_factor
    )


def compute_workload_safety(
    samples: Iterable[WorkloadSample],
    typical_baseline: float | None = None,
) -> float:
    """Return workload safety in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    today_index = max(_normalised_workload(s) for s in sample_list)

    if typical_baseline is None:
        # Without baseline, use absolute heuristic only.
        if today_index >= 0.85:
            return 0.0
        if today_index <= 0.50:
            return 1.0
        return max(0.0, 1.0 - (today_index - 0.50) / 0.35)

    deviation = today_index - typical_baseline
    if deviation <= 0:
        return 1.0
    # Acute:chronic spike of 0.30+ is high-risk per the
    # literature → safety 0.
    if deviation >= 0.30:
        return 0.0
    return max(0.0, 1.0 - deviation / 0.30)

"""Absent-swimmer signature.

A swimmer who entered the zone, hasn't been observed
surfacing for longer than a breath-hold window, and hasn't
left the zone is a classic silent-drowning candidate. The
library consumes presence heartbeats from the upstream
tracker — ``active=True`` means the swimmer was observed
in this tracker cycle — and reports the largest gap
between consecutive active samples.

Returns a unit-interval safety score where 1.0 = no
unexpected absence and 0.0 = absence at/above the urgent
threshold.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import SwimmerPresenceSample


def longest_absence_s(
    samples: Iterable[SwimmerPresenceSample],
) -> float:
    """Return the longest gap between consecutive
    ``active=True`` heartbeats (s).

    Uses timestamps so frame-rate variation doesn't
    distort the result.
    """
    sample_list = sorted(samples, key=lambda s: s.t_s)
    if not sample_list:
        return 0.0

    longest = 0.0
    last_active: float | None = None
    for s in sample_list:
        if s.active:
            if last_active is not None:
                longest = max(longest, s.t_s - last_active)
            last_active = s.t_s
    # Trailing gap (last active to end of window).
    if last_active is not None:
        longest = max(longest, sample_list[-1].t_s - last_active)
    return longest


def compute_absence_safety(
    samples: Iterable[SwimmerPresenceSample],
    watch_threshold_s: float = 20.0,
    urgent_threshold_s: float = 45.0,
) -> float:
    """Return absence safety score in [0, 1]."""
    gap = longest_absence_s(samples)
    if gap <= watch_threshold_s:
        return 1.0
    if gap >= urgent_threshold_s:
        return 0.0
    span = urgent_threshold_s - watch_threshold_s
    return max(0.0, min(1.0, 1.0 - (gap - watch_threshold_s) / span))

"""School-cohesion signature.

Schooling-behaviour metric. Tight, cohesive schooling is
the healthy resting state for salmonids; loss of cohesion
correlates with stressors (oxygen drop, predator pressure,
disease onset).

Returns unit-interval safety where 1.0 = tight cohesion
across the window, 0.0 = scattered / chaotic schooling.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import SchoolCohesionSample


SIGNATURE_VERSION = "school_cohesion@1.0.0"


_COHESION_WATCH = 0.55
_COHESION_URGENT = 0.30


def compute_school_cohesion_safety(
    samples: Iterable[SchoolCohesionSample],
) -> float:
    """Return school-cohesion safety in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    # Median cohesion across the window — robust to one
    # transient predator-pass startle.
    sorted_cohesion = sorted(s.cohesion for s in sample_list)
    mid = len(sorted_cohesion) // 2
    if len(sorted_cohesion) % 2:
        median = sorted_cohesion[mid]
    else:
        median = (sorted_cohesion[mid - 1] + sorted_cohesion[mid]) / 2

    if median >= _COHESION_WATCH:
        return 1.0
    if median <= _COHESION_URGENT:
        return 0.0
    span = _COHESION_WATCH - _COHESION_URGENT
    return max(0.0, (median - _COHESION_URGENT) / span)

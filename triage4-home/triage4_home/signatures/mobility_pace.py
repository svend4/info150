"""Mobility-pace trend — walking-speed estimate + decline slope.

Walking speed is a well-established wellness predictor in the
gerontology literature (Studenski 2011, "Gait Speed and
Survival in Older Adults", JAMA 305:50-58). Slower pace +
declining trend across days is a stronger signal than either
one alone.

The library reads room transitions — (from_room, to_room,
distance_m, timestamp) — and estimates pace in m/s per
transition. It returns:

- ``median_pace_mps`` — typical transit pace for the window.
- ``trend_score`` in [0, 1] where 1.0 = stable or improving
  (matches or exceeds baseline) and 0.0 = marked decline.

The library NEVER reports a specific clinical classification
("frail", "high fall risk") — pace is described as a trend
deviation, never as a clinical tier.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import RoomTransition


# Minimum sane pace to count — below this, the transition
# likely includes a stop (cup of tea in the kitchen) that
# shouldn't be counted as raw walking speed.
_MIN_PACE_MPS = 0.05

# Maximum sane pace to count — above this, the transition
# likely includes a sensor-mapping error (e.g. missing
# intermediate transition).
_MAX_PACE_MPS = 3.0


def compute_transition_paces(
    transitions: Iterable[RoomTransition],
) -> list[float]:
    """Return per-transition pace in m/s, filtered for sanity.

    Uses each transition's own ``duration_s`` as the transit
    time — NOT the time between transitions, which would
    include the time the resident spent in the previous
    room. Paces outside the sane range are dropped (likely
    sensor-mapping errors).
    """
    paces: list[float] = []
    for t in transitions:
        if t.duration_s <= 0:
            continue
        pace = t.distance_m / t.duration_s
        if _MIN_PACE_MPS <= pace <= _MAX_PACE_MPS:
            paces.append(pace)
    return paces


def compute_mobility_trend(
    transitions: Iterable[RoomTransition],
    baseline_median_mps: float | None = None,
    decline_threshold: float = 0.15,
) -> tuple[float, float]:
    """Return ``(median_pace_mps, trend_score)``.

    ``trend_score`` in [0, 1]:
    - 1.0 if current pace is ≥ baseline.
    - Linearly decreases as current drops below baseline,
      reaching 0.0 at (1 - decline_threshold) × baseline.
    - If no baseline is provided, returns 1.0 with a neutral
      trend score — the caller surfaces a "baseline pending"
      cue.
    """
    paces = compute_transition_paces(transitions)
    if not paces:
        # No usable pace data — neutral.
        return 0.0, 0.5

    # Median is robust to a single slow trip to the bathroom.
    sorted_paces = sorted(paces)
    mid = len(sorted_paces) // 2
    if len(sorted_paces) % 2 == 0:
        median = (sorted_paces[mid - 1] + sorted_paces[mid]) / 2
    else:
        median = sorted_paces[mid]

    if baseline_median_mps is None:
        return median, 1.0

    # Decline band: baseline to baseline × (1 - threshold)
    # maps to trend_score 1.0 → 0.0.
    if median >= baseline_median_mps:
        return median, 1.0
    decline_floor = baseline_median_mps * (1.0 - decline_threshold)
    if median <= decline_floor:
        return median, 0.0
    # Linear between the two.
    span = baseline_median_mps - decline_floor
    return median, max(0.0, min(1.0, (median - decline_floor) / span))

"""Wing-beat-frequency vitals signature.

Visual fallback channel — slow-flying / perched birds have
characteristic wing-beat frequencies. Out-of-band readings
correlate with stress / distress. Reads only ``reliable``
samples; if none reliable, score is neutral 1.0.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import WingbeatSample


# Generic wing-beat-frequency band (Hz). Real deployments
# tune per species; this is a placeholder spanning common
# medium-sized songbirds + waterfowl.
_LOW_HZ = 3.0
_HIGH_HZ = 12.0
_CAP_HZ = 25.0


def compute_wingbeat_safety(
    samples: Iterable[WingbeatSample],
) -> float:
    """Return wing-beat vitals safety score in [0, 1]."""
    reliable = [s for s in samples if s.reliable]
    if not reliable:
        return 1.0

    sorted_freqs = sorted(s.frequency_hz for s in reliable)
    mid = len(sorted_freqs) // 2
    if len(sorted_freqs) % 2:
        median = sorted_freqs[mid]
    else:
        median = (sorted_freqs[mid - 1] + sorted_freqs[mid]) / 2

    if _LOW_HZ <= median <= _HIGH_HZ:
        return 1.0
    if median >= _CAP_HZ:
        return 0.0
    if median > _HIGH_HZ:
        return max(0.0, 1.0 - (median - _HIGH_HZ) / (_CAP_HZ - _HIGH_HZ))
    # Below low — penalty scales linearly to 0 at half of low.
    if median <= _LOW_HZ / 2:
        return 0.0
    return (median - _LOW_HZ / 2) / (_LOW_HZ / 2)

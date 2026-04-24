"""Thermal-asymmetry signature.

Worst-sample-dominates over the observation window —
one clear focal hotspot through the pass is the
wound / inflammation signature, even if other samples
show nothing.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import ThermalSample


_NORMAL_CAP = 0.15
_CONCERN_CAP = 0.40


def compute_thermal_safety(
    samples: Iterable[ThermalSample],
) -> float:
    """Return thermal safety score in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    max_hotspot = max(s.hotspot for s in sample_list)

    if max_hotspot <= _NORMAL_CAP:
        return 1.0
    if max_hotspot >= _CONCERN_CAP:
        # Beyond concern cap, decay toward 0.
        span_above = 1.0 - _CONCERN_CAP
        over = max_hotspot - _CONCERN_CAP
        return max(0.0, 0.3 * (1.0 - over / span_above))
    # Linear decay in the normal → concern band.
    span = _CONCERN_CAP - _NORMAL_CAP
    into = max_hotspot - _NORMAL_CAP
    return 1.0 - 0.7 * (into / span)

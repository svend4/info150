"""Distress-call rate signature.

Returns the fraction of calls flagged with ``kind ==
'distress'`` (above a confidence threshold) and maps to a
unit-interval safety score where 1.0 = no distress calls,
0.0 = sustained distress vocalisation across the window.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import CallSample


_MIN_CONFIDENCE = 0.4
_DISTRESS_FRAC_HIGH = 0.30


def compute_distress_safety(
    samples: Iterable[CallSample],
) -> float:
    """Return distress safety score in [0, 1]."""
    sample_list = [s for s in samples if s.confidence >= _MIN_CONFIDENCE]
    if not sample_list:
        return 1.0

    distress_count = sum(1 for s in sample_list if s.kind == "distress")
    distress_frac = distress_count / len(sample_list)
    if distress_frac == 0:
        return 1.0
    if distress_frac >= _DISTRESS_FRAC_HIGH:
        return 0.0
    return max(0.0, min(1.0, 1.0 - distress_frac / _DISTRESS_FRAC_HIGH))

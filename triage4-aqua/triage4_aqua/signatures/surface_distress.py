"""Surface-distress signature.

A softer cousin to the full IDR classifier — picks up
swimmers whose head is consistently low on the water line
even if they haven't fully adopted the vertical posture
yet. Early-warning channel, distinct from idr_posture
which is the confirming pattern.

Returns a unit-interval safety score. Not independent of
``idr_posture`` (they share input), but correlates with
pre-IDR-window swimmers who may still be recoverable
without submersion.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import SurfacePoseSample


# Head-height risk — below this and sustained → distress
# signal.
_HEAD_LOW_RISK = 0.25


def compute_distress_safety(
    samples: Iterable[SurfacePoseSample],
) -> float:
    """Return surface-distress safety score in [0, 1].

    1.0 = no low-head samples. Linearly decreasing with
    fraction of low-head samples across the window;
    fraction ≥ 0.6 drops the score to 0.
    """
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    low_head = sum(1 for s in sample_list if s.head_height_rel <= _HEAD_LOW_RISK)
    frac = low_head / len(sample_list)
    if frac == 0:
        return 1.0
    if frac >= 0.6:
        return 0.0
    return max(0.0, min(1.0, 1.0 - frac / 0.6))

"""Crowd-flow signature.

The classic crush-precursor pattern: sustained unidirectional
inflow with high compaction into a choke point. Readings are
scored against the "net_direction + magnitude + compaction"
tuple on each FlowSample.

Returns a unit-interval safety score. 1.0 = flow state is
not a precursor (static / mixed / low-magnitude); 0.0 = clear
unidirectional compaction into choke point sustained across
the window.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import FlowSample


def compute_flow_safety(
    samples: Iterable[FlowSample],
) -> float:
    """Return flow safety score in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    # A flow sample is a precursor when:
    #  * net_direction == "in" (or out, for crush-out like
    #    the 2022 Itaewon alley egress)
    #  * magnitude is high
    #  * compaction is high
    # The combined score uses magnitude × compaction as the
    # precursor intensity, but only when direction is "in"
    # or "out" (static / crossflow / mixed net to zero
    # precursor signal).
    worst = 1.0
    for s in sample_list:
        if s.net_direction in ("in", "out"):
            precursor = s.magnitude * s.compaction
            sample_safety = 1.0 - precursor
        else:
            sample_safety = 1.0
        worst = min(worst, sample_safety)
    return max(0.0, min(1.0, worst))

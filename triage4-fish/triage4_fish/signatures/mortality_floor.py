"""Mortality-floor signature.

Counts confidence-weighted dead-fish-on-bottom candidates
across the window. Returns unit-interval safety where 1.0
= no detected mortality on the pen floor, 0.0 = sustained
mortality cluster.

Mortality clusters trigger the surveillance-overreach-
safe wording in the engine (combined with low gill rate
or poor water chemistry, the engine surfaces a "candidate
disease pattern — vet review recommended" framing —
NEVER an "outbreak detected" framing).
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import MortalityFloorSample


SIGNATURE_VERSION = "mortality_floor@1.0.0"


_HIGH_WEIGHTED_COUNT = 30.0


def compute_mortality_safety(
    samples: Iterable[MortalityFloorSample],
) -> float:
    """Return mortality-floor safety in [0, 1]."""
    sample_list = [s for s in samples if s.confidence >= 0.40]
    if not sample_list:
        return 1.0

    # Confidence-weighted total count.
    weighted_total = sum(s.count * s.confidence for s in sample_list)
    if weighted_total >= _HIGH_WEIGHTED_COUNT:
        return 0.0
    return max(0.0, min(1.0, 1.0 - weighted_total / _HIGH_WEIGHTED_COUNT))

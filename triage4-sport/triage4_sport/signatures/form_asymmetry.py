"""Form-asymmetry signature.

Reads ``MovementSample`` records and returns a unit-interval
safety score where 1.0 = symmetric form, 0.0 = persistent
one-sided pattern.

Compares against an athlete's typical baseline: deviation
above baseline drives the score down faster than absolute
asymmetry alone (an athlete with a typical 0.4 asymmetry
who shows 0.5 today is less concerning than an athlete
with typical 0.1 who shows 0.5 today).
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import MovementSample


SIGNATURE_VERSION = "form_asymmetry@1.0.0"


_DEVIATION_HIGH = 0.30


def compute_form_asymmetry_safety(
    samples: Iterable[MovementSample],
    typical_baseline: float | None = None,
) -> float:
    """Return form-asymmetry safety in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    sorted_asym = sorted(s.form_asymmetry for s in sample_list)
    mid = len(sorted_asym) // 2
    if len(sorted_asym) % 2:
        median_asym = sorted_asym[mid]
    else:
        median_asym = (sorted_asym[mid - 1] + sorted_asym[mid]) / 2

    if typical_baseline is None:
        # No baseline → use absolute asymmetry only.
        if median_asym <= 0.20:
            return 1.0
        if median_asym >= 0.55:
            return 0.0
        return max(0.0, 1.0 - (median_asym - 0.20) / 0.35)

    # Compute deviation above baseline. Below baseline → 1.0.
    deviation = median_asym - typical_baseline
    if deviation <= 0:
        return 1.0
    if deviation >= _DEVIATION_HIGH:
        return 0.0
    return max(0.0, 1.0 - deviation / _DEVIATION_HIGH)

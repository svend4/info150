"""Postural-collapse signature.

Reads ``QuadrupedPoseSample.body_upright`` across the
observation and distinguishes ordinary rest (body_upright
can be low briefly, recovers) from a down-and-not-rising
pattern (body_upright stays low for the majority of the
window).

Returns unit-interval safety score — 1.0 = upright /
ordinary-rest; 0.0 = sustained down-pose.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import QuadrupedPoseSample


_LOW_UPRIGHT_THRESHOLD = 0.3


def compute_postural_safety(
    samples: Iterable[QuadrupedPoseSample],
) -> float:
    """Return postural-collapse safety score in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    low_fraction = sum(
        1 for s in sample_list if s.body_upright < _LOW_UPRIGHT_THRESHOLD
    ) / len(sample_list)

    if low_fraction == 0:
        return 1.0
    # Fraction < 0.25 = ordinary rest / grazing low-head
    # postures; score stays high.
    if low_fraction <= 0.25:
        return 1.0 - 0.2 * (low_fraction / 0.25)
    # Fraction in 0.25-0.75: linear decay.
    if low_fraction <= 0.75:
        span = 0.75 - 0.25
        return max(0.0, 0.8 - 0.6 * ((low_fraction - 0.25) / span))
    # Fraction > 0.75: sustained down pattern.
    return max(0.0, 0.2 - 0.2 * ((low_fraction - 0.75) / 0.25))

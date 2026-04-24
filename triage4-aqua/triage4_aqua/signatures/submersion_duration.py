"""Submersion-duration signature.

The dominant drowning signal in the aquatic-safety
literature: the longest consecutive below-surface run
exceeding a zone-specific threshold.

Healthy breath-hold for a casual swimmer is typically
10-20 s; competitive freedivers tolerate much longer but
are not the audience for a general pool-watch system.
Past ~30 s in a non-training context, the window is in
the "lifeguard attention required" zone regardless of
cause. The drowning window itself is 4-6 min before
permanent neurological injury per WHO / Red Cross data.

Signature returns a unit-interval safety score where 1.0
= no significant submersion and 0.0 = submersion ≥ the
urgent threshold.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import SubmersionSample


def longest_submersion_s(
    samples: Iterable[SubmersionSample],
) -> float:
    """Return the longest consecutive below-surface run (s).

    Uses sample timestamps so variable frame rates don't
    distort the result.
    """
    sample_list = sorted(samples, key=lambda s: s.t_s)
    if not sample_list:
        return 0.0

    longest = 0.0
    run_start: float | None = None
    for sample in sample_list:
        if sample.submerged:
            if run_start is None:
                run_start = sample.t_s
        else:
            if run_start is not None:
                longest = max(longest, sample.t_s - run_start)
                run_start = None
    if run_start is not None:
        longest = max(longest, sample_list[-1].t_s - run_start)
    return longest


def compute_submersion_safety(
    samples: Iterable[SubmersionSample],
    watch_threshold_s: float = 15.0,
    urgent_threshold_s: float = 30.0,
) -> float:
    """Return submersion safety score in [0, 1].

    1.0 = longest run below the watch threshold.
    0.0 = longest run at or above the urgent threshold.
    Linear in the band between.
    """
    longest = longest_submersion_s(samples)
    if longest <= watch_threshold_s:
        return 1.0
    if longest >= urgent_threshold_s:
        return 0.0
    span = urgent_threshold_s - watch_threshold_s
    return max(0.0, min(1.0, 1.0 - (longest - watch_threshold_s) / span))

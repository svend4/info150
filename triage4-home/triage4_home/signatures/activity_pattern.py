"""ADL-deviation score from activity buckets.

Activities of Daily Living (ADL) monitoring reads how today's
activity mix compares to the resident's own recent baseline.
A large deviation (e.g. twice the resting time / half the
moderate time) earns a low alignment score and a caregiver
check-in cue.

Baseline-only. Never compared to a healthy-adult norm — see
docs/PHILOSOPHY.md on the dignity boundary.

Coverage quality: if a large fraction of the window is
``unknown`` (sensors offline, resident outside), the alignment
score is capped — caller can see that the baseline comparison
is lower-confidence than usual.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..core.enums import ActivityIntensity
from ..core.models import ActivitySample


@dataclass(frozen=True)
class ActivityFractions:
    """Fraction of the window spent in each bucket. Sum ≤ 1
    (remaining portion is "unknown" / uncovered)."""

    resting: float
    light: float
    moderate: float

    @property
    def coverage(self) -> float:
        return self.resting + self.light + self.moderate


def compute_fractions(samples: Iterable[ActivitySample]) -> ActivityFractions:
    """Return the activity fraction breakdown for the window.

    Uses sample counts as the weighting — samples are assumed
    to be at a regular rate. If irregular, upstream should
    resample before passing in.
    """
    sample_list = list(samples)
    n = len(sample_list)
    if n == 0:
        return ActivityFractions(resting=0.0, light=0.0, moderate=0.0)
    counts: dict[ActivityIntensity, int] = {
        "resting": 0,
        "light": 0,
        "moderate": 0,
        "unknown": 0,
    }
    for s in sample_list:
        counts[s.intensity] += 1
    return ActivityFractions(
        resting=counts["resting"] / n,
        light=counts["light"] / n,
        moderate=counts["moderate"] / n,
    )


def compute_activity_alignment(
    current: Iterable[ActivitySample],
    baseline: ActivityFractions | None,
) -> float:
    """Return an alignment score in [0, 1].

    1.0 = current matches baseline exactly.
    0.0 = maximally different fractions.

    If no baseline is supplied, returns 1.0 with a neutral
    score — the caller is responsible for surfacing a
    "baseline not yet established" cue.
    """
    fractions = compute_fractions(current)
    if fractions.coverage < 0.2:
        # Very little observation data — cannot make a fair
        # alignment call. Return 0.5 as a neutral score.
        return 0.5
    if baseline is None:
        return 1.0

    # L1 distance between the two fraction vectors, mapped to
    # [0, 1]. Max L1 between two 3-dim probability-like
    # vectors (each sums to at most 1) is 2.0.
    diff = (
        abs(fractions.resting - baseline.resting)
        + abs(fractions.light - baseline.light)
        + abs(fractions.moderate - baseline.moderate)
    )
    alignment = 1.0 - min(1.0, diff / 2.0)

    # Low-coverage windows scale the alignment back toward
    # 1.0 — "not enough data to be sure" shouldn't trigger a
    # low score.
    coverage_weight = min(1.0, fractions.coverage / 0.6)
    return max(0.0, min(1.0, 1.0 - coverage_weight * (1.0 - alignment)))

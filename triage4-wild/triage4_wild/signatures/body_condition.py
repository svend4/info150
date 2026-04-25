"""Body-condition signature — emaciation indicator.

Reads ``BodyConditionSample.condition_score`` across the
observation and returns the mean. Lower scores indicate
emaciation / poor body condition, which is a downstream
flag for reserve-vet review.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import BodyConditionSample


def compute_body_condition_safety(
    samples: Iterable[BodyConditionSample],
) -> float:
    """Return body-condition safety score in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    mean_score = sum(s.condition_score for s in sample_list) / len(sample_list)
    return max(0.0, min(1.0, mean_score))

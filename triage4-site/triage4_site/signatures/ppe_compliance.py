"""PPE-compliance signature.

Takes a list of PPE samples + the zone-required PPE set, and
reports the fraction of samples where every required item was
detected. The result is a unit-interval compliance score.

Note on labor-relations boundary: this signature produces a
per-observation compliance number. Consumer apps are
expected to aggregate to zone / shift level before routing
anywhere — never to roll the number up as a per-worker
performance metric. See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from typing import Iterable

from ..core.enums import PPEItem
from ..core.models import PPESample


def compute_ppe_compliance(
    samples: Iterable[PPESample],
    required_ppe: tuple[PPEItem, ...],
) -> float:
    """Return compliance fraction in [0, 1].

    With no required PPE items, the zone is implicitly
    compliant and the score is 1.0 (a consumer app that
    doesn't configure required_ppe shouldn't see a
    false alert).

    With no samples, returns 0.0 — the calibration-layer
    cue surfaces the lack of coverage separately.
    """
    required = set(required_ppe)
    if not required:
        return 1.0
    sample_list = list(samples)
    if not sample_list:
        return 0.0
    compliant = sum(
        1 for s in sample_list
        if required.issubset(set(s.items_detected))
    )
    return compliant / len(sample_list)

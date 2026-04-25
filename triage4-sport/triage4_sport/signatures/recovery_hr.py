"""Recovery-HR signature.

Reads post-effort HR-recovery snapshots and returns a
safety score. A 1-min HR drop of >= 30 bpm is reassuring
(well-conditioned recovery); < 12 bpm is poor recovery.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import RecoveryHRSample


SIGNATURE_VERSION = "recovery_hr@1.0.0"


_GOOD_DROP = 30.0
_POOR_DROP = 12.0


def compute_recovery_hr_safety(
    samples: Iterable[RecoveryHRSample],
    typical_baseline_bpm: float | None = None,
) -> float:
    """Return recovery-HR safety in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    mean_drop = sum(s.recovery_drop_bpm for s in sample_list) / len(sample_list)

    if mean_drop >= _GOOD_DROP:
        return 1.0
    if mean_drop <= _POOR_DROP:
        return 0.0

    base_score = (mean_drop - _POOR_DROP) / (_GOOD_DROP - _POOR_DROP)

    # Compare to athlete baseline if supplied.
    if typical_baseline_bpm is None:
        return max(0.0, min(1.0, base_score))

    deviation = typical_baseline_bpm - mean_drop
    if deviation <= 0:
        return max(0.0, min(1.0, base_score))
    # Significant degradation from baseline drops the score
    # further.
    deviation_factor = max(0.0, 1.0 - deviation / 15.0)
    return max(0.0, min(1.0, base_score * deviation_factor))

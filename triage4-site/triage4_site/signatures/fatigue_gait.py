"""Fatigue-gait signature.

Two inputs per sample:
- pace_mps (walking speed over a short window)
- asymmetry (left-right step-length mismatch)

Fatigue tells show up as a combination of:
- pace declining across the shift vs. an early-shift baseline
- asymmetry rising (tired workers favour one side)

The signature picks up both. Returns a unit-interval
safety score; 1.0 = fresh gait, 0.0 = marked fatigue
pattern.

NB: never diagnoses "exhaustion" — that's a clinical word,
see the claims-guard list in core/models.py.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import FatigueGaitSample


# Relative pace decline that counts as clearly fatigued.
_SEVERE_PACE_DROP = 0.30
# Asymmetry level that counts as clearly fatigued.
_SEVERE_ASYMMETRY = 0.25


def compute_fatigue_safety(
    samples: Iterable[FatigueGaitSample],
) -> float:
    """Return fatigue-safety score in [0, 1].

    Compares early-shift vs. late-shift pace (first third
    vs. last third of samples). Low sample count returns a
    neutral 1.0 — calibration layer surfaces the gap.
    """
    sample_list = sorted(samples, key=lambda s: s.t_s)
    if len(sample_list) < 6:
        return 1.0

    third = max(1, len(sample_list) // 3)
    early = sample_list[:third]
    late = sample_list[-third:]

    early_pace = sum(s.pace_mps for s in early) / len(early)
    late_pace = sum(s.pace_mps for s in late) / len(late)

    pace_score = 1.0
    if early_pace > 0 and late_pace < early_pace:
        drop = (early_pace - late_pace) / early_pace
        if drop >= _SEVERE_PACE_DROP:
            pace_score = 0.0
        else:
            pace_score = 1.0 - drop / _SEVERE_PACE_DROP

    late_asymmetry = sum(s.asymmetry for s in late) / len(late)
    asymmetry_score = 1.0
    if late_asymmetry > 0:
        if late_asymmetry >= _SEVERE_ASYMMETRY:
            asymmetry_score = 0.0
        else:
            asymmetry_score = 1.0 - late_asymmetry / _SEVERE_ASYMMETRY

    # Average of the two channels — either can pull the
    # score down on its own, and both together pull it
    # lower still.
    return max(0.0, min(1.0, (pace_score + asymmetry_score) / 2.0))

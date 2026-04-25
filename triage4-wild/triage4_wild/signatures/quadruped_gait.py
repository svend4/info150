"""Quadruped-gait signature.

Reads per-frame ``QuadrupedPoseSample`` + ``GaitSample``
records and returns a unit-interval safety score. 1.0 =
symmetric, rhythmic gait typical of a healthy animal;
0.0 = strong lameness signature.

Species-agnostic. Species-specific escalation lives in
the engine — this signature just measures asymmetry +
cadence steadiness.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import GaitSample, QuadrupedPoseSample


_ASYMMETRY_WATCH = 0.25
_ASYMMETRY_URGENT = 0.55


def compute_gait_safety(
    pose_samples: Iterable[QuadrupedPoseSample],
    gait_samples: Iterable[GaitSample],
) -> float:
    """Return gait safety score in [0, 1]."""
    pose_list = list(pose_samples)
    if not pose_list:
        return 1.0

    # Median limb asymmetry — robust to one flinch frame.
    sorted_asym = sorted(p.limb_asymmetry for p in pose_list)
    mid = len(sorted_asym) // 2
    if len(sorted_asym) % 2:
        median_asym = sorted_asym[mid]
    else:
        median_asym = (sorted_asym[mid - 1] + sorted_asym[mid]) / 2

    if median_asym <= _ASYMMETRY_WATCH:
        asym_score = 1.0
    elif median_asym >= _ASYMMETRY_URGENT:
        asym_score = 0.0
    else:
        span = _ASYMMETRY_URGENT - _ASYMMETRY_WATCH
        asym_score = 1.0 - (median_asym - _ASYMMETRY_WATCH) / span

    # Cadence-steadiness multiplier if gait samples present.
    gait_list = list(gait_samples)
    if gait_list:
        mean_cadence = sum(
            g.cadence_steadiness for g in gait_list
        ) / len(gait_list)
        # 0.6 → 1.0 multiplier.
        cadence_mult = 0.6 + 0.4 * mean_cadence
    else:
        cadence_mult = 1.0

    return max(0.0, min(1.0, asym_score * cadence_mult))

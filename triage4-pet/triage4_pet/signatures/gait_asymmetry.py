"""Gait-asymmetry signature.

Reads per-cycle ``GaitSample`` records and returns a
unit-interval safety score. 1.0 = symmetric rhythmic gait,
0.0 = strong lameness signature across the window.

Species-agnostic at this layer — the engine applies per-
species weighting after the signature returns. A quadruped
gait is measured the same way regardless of species;
what varies is what's "normal" for that species' activity
level in a home-video setting.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import GaitSample


# Asymmetry that marks a clear one-sided lameness. Above this
# in the median sample = urgent-band signal.
_ASYMMETRY_URGENT = 0.50

# Asymmetry that's a "watch" signal — noticeable but not
# obviously lame.
_ASYMMETRY_WATCH = 0.25


def compute_gait_safety(samples: Iterable[GaitSample]) -> float:
    """Return gait safety score in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    # Use the median asymmetry (robust to a single flinch).
    sorted_asym = sorted(s.limb_asymmetry for s in sample_list)
    mid = len(sorted_asym) // 2
    if len(sorted_asym) % 2:
        asym = sorted_asym[mid]
    else:
        asym = (sorted_asym[mid - 1] + sorted_asym[mid]) / 2

    if asym <= _ASYMMETRY_WATCH:
        return 1.0
    if asym >= _ASYMMETRY_URGENT:
        return 0.0
    span = _ASYMMETRY_URGENT - _ASYMMETRY_WATCH
    gait_score = 1.0 - (asym - _ASYMMETRY_WATCH) / span

    # Pace consistency multiplier — non-rhythmic gait earns
    # an additional score drop.
    avg_consistency = sum(s.pace_consistency for s in sample_list) / len(sample_list)
    # At consistency 0 → multiplier 0.6; at 1.0 → multiplier 1.0.
    consistency_multiplier = 0.6 + 0.4 * avg_consistency
    return max(0.0, min(1.0, gait_score * consistency_multiplier))

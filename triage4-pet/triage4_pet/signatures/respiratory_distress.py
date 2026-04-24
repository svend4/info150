"""Respiratory-distress signature.

Scores RR against a species-specific resting band with a
"panting at rest" adjustment (a pain / distress signal in
dogs especially, but also cats and rabbits).

Returns a unit-interval safety score. 1.0 = RR inside the
resting band with no panting-at-rest; 0.0 = RR well above
the upper cap OR sustained panting-at-rest.
"""

from __future__ import annotations

from typing import Iterable

from ..core.enums import SpeciesKind
from ..core.models import BreathingSample


# (resting_low, resting_high, cap) per species, in breaths
# per minute. Cap = rate above which the score reaches 0.
# Values drawn from the MSD Veterinary Manual 2022
# reference tables (healthy adult, resting).
_BANDS: dict[SpeciesKind, tuple[float, float, float]] = {
    "dog":    (10, 30, 60),
    "cat":    (20, 30, 60),
    "horse":  (8,  16, 40),
    "rabbit": (30, 60, 120),
}


def compute_respiratory_safety(
    samples: Iterable[BreathingSample],
    species: SpeciesKind,
) -> float:
    """Return respiratory safety score in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0
    if species not in _BANDS:
        raise KeyError(f"no respiratory band for species {species!r}")

    lo, hi, cap = _BANDS[species]

    # Median rate across the window. Robust to a single
    # panting burst mid-video.
    sorted_rates = sorted(s.rate_bpm for s in sample_list)
    mid = len(sorted_rates) // 2
    if len(sorted_rates) % 2:
        median_rate = sorted_rates[mid]
    else:
        median_rate = (sorted_rates[mid - 1] + sorted_rates[mid]) / 2

    if lo <= median_rate <= hi:
        rate_score = 1.0
    elif median_rate >= cap:
        rate_score = 0.0
    elif median_rate > hi:
        # Between hi and cap: linear decay.
        rate_score = max(0.0, 1.0 - (median_rate - hi) / (cap - hi))
    else:
        # Below resting band — bradypnea, also concerning.
        # Linear decay to 0 at lo/2.
        if median_rate <= lo / 2:
            rate_score = 0.0
        else:
            rate_score = (median_rate - lo / 2) / (lo / 2)

    # Panting-at-rest adjustment: if any sample flagged
    # at_rest=True with rate > hi, weight the score down.
    panting_at_rest = sum(
        1 for s in sample_list if s.at_rest and s.rate_bpm > hi
    )
    if panting_at_rest >= 1:
        at_rest_frac = panting_at_rest / max(1, len(sample_list))
        rate_score *= max(0.0, 1.0 - at_rest_frac)

    return max(0.0, min(1.0, rate_score))

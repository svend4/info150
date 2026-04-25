"""Gill-rate signature.

Pen-aggregate gill rate (Eulerian-derived) compared
against a species reference band. Returns unit-interval
safety where 1.0 = within the resting band, 0.0 = well
outside in either direction.

Bands sourced from aquaculture literature reference values
(e.g. Atlantic salmon resting opercular rate ≈ 60-100 bpm
at 10°C; rises with temperature). Real deployments tune
per pen + per season.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import GillRateSample, Species


SIGNATURE_VERSION = "gill_rate@1.0.0"


# (lo, hi, low_cap, high_cap) per species in bpm.
_BANDS: dict[Species, tuple[float, float, float, float]] = {
    "salmon":   (60,  100, 35, 150),
    "trout":    (50,  90,  30, 140),
    "sea_bass": (40,  80,  25, 130),
    "tilapia":  (50,  100, 30, 150),
    "unknown":  (50,  100, 30, 150),
}


def compute_gill_rate_safety(
    samples: Iterable[GillRateSample],
    species: Species,
) -> float:
    """Return gill-rate safety in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0
    if species not in _BANDS:
        raise KeyError(f"no band for species {species!r}")

    lo, hi, low_cap, high_cap = _BANDS[species]

    sorted_rates = sorted(s.rate_bpm for s in sample_list)
    mid = len(sorted_rates) // 2
    if len(sorted_rates) % 2:
        median = sorted_rates[mid]
    else:
        median = (sorted_rates[mid - 1] + sorted_rates[mid]) / 2

    if lo <= median <= hi:
        return 1.0
    if median >= high_cap or median <= low_cap:
        return 0.0
    if median > hi:
        return max(0.0, 1.0 - (median - hi) / (high_cap - hi))
    return max(0.0, 1.0 - (lo - median) / (lo - low_cap))

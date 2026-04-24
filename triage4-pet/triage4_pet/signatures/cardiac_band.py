"""Cardiac-band signature.

Scores HR against a species-specific resting band. HR
estimation from a phone video via Eulerian magnification
is less reliable than a clinic-grade stethoscope, so the
signature reads the ``reliable`` flag and returns a neutral
score for unreliable readings.

Returns a unit-interval safety score. 1.0 = HR inside the
resting band OR all readings unreliable; 0.0 = HR well
outside the cap.
"""

from __future__ import annotations

from typing import Iterable

from ..core.enums import SpeciesKind
from ..core.models import VitalHRSample


# (resting_low, resting_high, low_cap, high_cap) per species
# in beats per minute. MSD Veterinary Manual 2022 reference
# tables. The cap numbers represent HR values well outside
# the normal range in either direction — below low_cap is
# bradycardia, above high_cap is tachycardia.
_BANDS: dict[SpeciesKind, tuple[float, float, float, float]] = {
    #              (lo,  hi,  low_cap, high_cap)
    "dog":        (60,  140, 40,  200),
    "cat":        (140, 220, 100, 260),
    "horse":      (30,  45,  22,  90),
    "rabbit":     (130, 325, 100, 400),
}


def compute_cardiac_safety(
    samples: Iterable[VitalHRSample],
    species: SpeciesKind,
) -> float:
    """Return cardiac safety score in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0
    if species not in _BANDS:
        raise KeyError(f"no cardiac band for species {species!r}")

    # Only score reliable readings. If none are reliable,
    # return a neutral 1.0 — calibration layer surfaces
    # the reliability gap separately.
    reliable = [s for s in sample_list if s.reliable]
    if not reliable:
        return 1.0

    lo, hi, low_cap, high_cap = _BANDS[species]

    # Median of reliable samples.
    sorted_hrs = sorted(s.hr_bpm for s in reliable)
    mid = len(sorted_hrs) // 2
    if len(sorted_hrs) % 2:
        median_hr = sorted_hrs[mid]
    else:
        median_hr = (sorted_hrs[mid - 1] + sorted_hrs[mid]) / 2

    if lo <= median_hr <= hi:
        return 1.0
    if median_hr >= high_cap or median_hr <= low_cap:
        return 0.0
    if median_hr > hi:
        return max(0.0, 1.0 - (median_hr - hi) / (high_cap - hi))
    # Below lo.
    return max(0.0, 1.0 - (lo - median_hr) / (lo - low_cap))

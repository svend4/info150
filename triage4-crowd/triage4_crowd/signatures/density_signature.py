"""Zone density signature.

Helbing 2007 / Fruin 1971 bands map persons-per-m² to four
qualitative states: comfortable, dense, near-critical,
critical. This module returns a density safety score where
1.0 = textbook-comfortable crowd and 0.0 = critical density.

Per-zone-kind bands are distinct — a music-festival standing
area tolerates higher density than a transit platform before
the near-critical band begins. Default cut-offs reflect the
published literature for each kind; real deployments tune
per-venue.
"""

from __future__ import annotations

from typing import Iterable

from ..core.enums import ZoneKind
from ..core.models import DensityReading


# Per-zone-kind thresholds. ``comfort`` = upper limit of the
# comfortable band; ``dense`` = upper limit of the dense
# band; ``critical`` = density at which the score reaches 0.
# Values in persons per m².
_BANDS: dict[ZoneKind, tuple[float, float, float]] = {
    #                 (comfort, dense, critical)
    "seating":        (1.5,     2.5,   4.0),
    "standing":       (2.0,     4.0,   6.0),
    "egress":         (1.0,     2.0,   3.5),
    "transit_platform": (1.2,   2.5,   4.5),
    "concourse":      (1.5,     3.0,   5.0),
}


def compute_density_safety(
    readings: Iterable[DensityReading],
    zone_kind: ZoneKind,
) -> float:
    """Return density safety score in [0, 1].

    1.0 = median reading inside the comfort band.
    0.0 = median reading at or above the critical band.
    Intermediate values scale linearly.

    Empty input returns 1.0 — calibration layer surfaces the
    data gap separately.
    """
    reading_list = list(readings)
    if not reading_list:
        return 1.0
    if zone_kind not in _BANDS:
        raise KeyError(f"no density band for zone_kind {zone_kind!r}")

    comfort, dense, critical = _BANDS[zone_kind]

    # Use the median reading — one spike shouldn't tank the
    # score. Sustained elevation is what the pressure +
    # flow channels read.
    sorted_vals = sorted(r.persons_per_m2 for r in reading_list)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2:
        median = sorted_vals[mid]
    else:
        median = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2

    if median <= comfort:
        return 1.0
    if median >= critical:
        return 0.0
    if median <= dense:
        # Comfort → dense maps 1.0 → 0.5.
        span = dense - comfort
        return 1.0 - 0.5 * (median - comfort) / span
    # Dense → critical maps 0.5 → 0.0.
    span = critical - dense
    return max(0.0, 0.5 - 0.5 * (median - dense) / span)

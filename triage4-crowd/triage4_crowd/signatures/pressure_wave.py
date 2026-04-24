"""Crowd-pressure signature.

Helbing 2007 identifies "crowd pressure" — an integrated
acceleration-jerk-density quantity — as the most reliable
precursor to crush events, and more discriminating than
density alone. This module assumes the upstream hub produces
already-normalised ``pressure_rms`` values in [0, 1] and
reads them as a time series.

Score = the sustained-high fraction of the window, mapped to
a safety score. Occasional spikes in a normal crowd are OK;
sustained elevation is the precursor.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import PressureReading


# Pressure thresholds (dimensionless, [0, 1]). ``elevated``
# = upper end of normal variation; ``high`` = sustained
# reading above this is the precursor signal.
_ELEVATED = 0.35
_HIGH = 0.60


def compute_pressure_safety(
    readings: Iterable[PressureReading],
) -> float:
    """Return pressure safety score in [0, 1].

    1.0 = no elevated samples. 0.0 = majority of samples
    above the high threshold.
    """
    reading_list = list(readings)
    if not reading_list:
        return 1.0

    # Fraction of readings in each band.
    elevated_frac = sum(
        1 for r in reading_list if r.pressure_rms >= _ELEVATED
    ) / len(reading_list)
    high_frac = sum(
        1 for r in reading_list if r.pressure_rms >= _HIGH
    ) / len(reading_list)

    # Score shape: elevated samples alone don't break the
    # score below 0.5; sustained high samples drive it to 0.
    elevated_penalty = min(1.0, elevated_frac * 0.7)
    high_penalty = min(1.0, high_frac * 1.5)
    safety = 1.0 - max(elevated_penalty, high_penalty)
    return max(0.0, min(1.0, safety))

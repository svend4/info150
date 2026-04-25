"""Febrile-thermal signature.

Mean elevation across IR samples; high values are an
avian-flu surveillance trigger but the library NEVER
flags this as "flu" — the engine routes the signal to a
``thermal`` alert kind that pairs with mortality_cluster
to produce a "candidate mortality cluster — sampling
recommended" framing in the alert text.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import BodyThermalSample


def compute_febrile_thermal_safety(
    samples: Iterable[BodyThermalSample],
) -> float:
    """Return thermal safety score in [0, 1].

    1.0 = no elevation; 0.0 = sustained marked elevation.
    """
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    mean_elev = sum(s.elevation for s in sample_list) / len(sample_list)
    return max(0.0, min(1.0, 1.0 - mean_elev))

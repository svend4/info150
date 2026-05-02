"""Threshold bands for mapping channel safety scores to alert levels.

Defaults are demo placeholders. Real deployments tune bands per
coast/zone with paired-data.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import ZoneKind


@dataclass(frozen=True)
class CoastSafetyBands:
    """Threshold bands for the coast-safety engine.

    Convention: a *_watch / *_urgent pair such that
    ``score < watch`` raises a watch alert and
    ``score < urgent`` raises an urgent alert.
    """

    density_watch: float = 0.55
    density_urgent: float = 0.30

    drowning_watch: float = 0.65
    drowning_urgent: float = 0.40

    sun_watch: float = 0.55
    sun_urgent: float = 0.40


_BEACH = CoastSafetyBands()
_PROMENADE = CoastSafetyBands(
    density_watch=0.50, density_urgent=0.25,
    sun_watch=0.45, sun_urgent=0.30,
)
_WATER = CoastSafetyBands(
    density_watch=0.50, density_urgent=0.30,
    drowning_watch=0.70, drowning_urgent=0.45,
    sun_watch=0.55, sun_urgent=0.40,
)
_PIER = CoastSafetyBands(
    density_watch=0.60, density_urgent=0.40,
    sun_watch=0.50, sun_urgent=0.35,
)


_BANDS: dict[ZoneKind, CoastSafetyBands] = {
    "beach": _BEACH,
    "promenade": _PROMENADE,
    "water": _WATER,
    "pier": _PIER,
}


def band_for(zone_kind: ZoneKind) -> CoastSafetyBands:
    if zone_kind not in _BANDS:
        raise KeyError(f"no bands for zone_kind {zone_kind!r}")
    return _BANDS[zone_kind]


__all__ = ["CoastSafetyBands", "band_for"]

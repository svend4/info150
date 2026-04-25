"""Water-chemistry signature.

Reads ``WaterChemistrySample`` records and returns BOTH a
unit-interval safety score AND a turbidity scaling factor
that the engine uses to weight the visible-light channels.

This dual return is the signature-layer reflection of the
multi-modal-fusion architecture: water chemistry is both a
safety channel in its own right AND a confidence input
that scales the vision channels.

DO bands (mg/L): salmon needs >= 6, watch < 5, urgent < 3.
Temperature (°C): salmon comfortable 6-14, watch 14-18,
urgent > 18.
Salinity: species-dependent — salmon adapt 28-35 ppt
typical, sea bass tolerate wider; tilapia is freshwater.
Turbidity (NTU): clear < 5, turbid 5-50, silt-storm > 50.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..core.models import Species, WaterChemistrySample


SIGNATURE_VERSION = "water_chemistry@1.0.0"


@dataclass(frozen=True)
class WaterChemistryReading:
    """Per-window water-chemistry summary.

    ``safety`` is the unit-interval channel score the engine
    fuses with the vision channels. ``vision_confidence``
    scales the engine's vision-channel weights — high
    turbidity → reduced vision confidence → vision channels
    blend toward neutral.
    """

    safety: float
    vision_confidence: float


# (do_lo, do_watch, do_urgent) per species in mg/L.
_DO_BANDS: dict[Species, tuple[float, float, float]] = {
    "salmon":   (6.0, 5.0, 3.0),
    "trout":    (6.0, 5.0, 3.0),
    "sea_bass": (5.5, 4.5, 2.5),
    "tilapia":  (4.0, 3.0, 1.5),
    "unknown":  (5.5, 4.5, 2.5),
}

# (temp_low_ok, temp_high_ok, temp_urgent_high) per species °C.
_TEMP_BANDS: dict[Species, tuple[float, float, float]] = {
    "salmon":   (6.0, 14.0, 18.0),
    "trout":    (6.0, 16.0, 20.0),
    "sea_bass": (10.0, 22.0, 28.0),
    "tilapia":  (22.0, 30.0, 35.0),
    "unknown":  (8.0, 22.0, 28.0),
}


def _do_safety(do: float, species: Species) -> float:
    do_lo, do_watch, do_urgent = _DO_BANDS[species]
    if do >= do_lo:
        return 1.0
    if do <= do_urgent:
        return 0.0
    if do >= do_watch:
        return max(0.0, 1.0 - (do_lo - do) / (do_lo - do_watch) * 0.5)
    return max(0.0, 0.5 - (do_watch - do) / (do_watch - do_urgent) * 0.5)


def _temp_safety(temp: float, species: Species) -> float:
    lo, hi, urgent = _TEMP_BANDS[species]
    if lo <= temp <= hi:
        return 1.0
    if temp >= urgent:
        return 0.0
    if temp > hi:
        return max(0.0, 1.0 - (temp - hi) / (urgent - hi))
    if temp < lo:
        # Cold-side: linear decay to 0 at temp < lo - 5.
        floor = lo - 5.0
        if temp <= floor:
            return 0.0
        return (temp - floor) / 5.0
    return 1.0


def _turbidity_to_vision_confidence(turbidity_ntu: float) -> float:
    if turbidity_ntu <= 5.0:
        return 1.0
    if turbidity_ntu >= 50.0:
        return 0.3
    return max(0.3, 1.0 - 0.7 * (turbidity_ntu - 5.0) / 45.0)


def compute_water_chemistry(
    samples: Iterable[WaterChemistrySample],
    species: Species,
) -> WaterChemistryReading:
    """Return ``WaterChemistryReading`` — safety + vision_confidence."""
    sample_list = list(samples)
    if not sample_list:
        return WaterChemistryReading(safety=1.0, vision_confidence=1.0)
    if species not in _DO_BANDS or species not in _TEMP_BANDS:
        raise KeyError(f"no water bands for species {species!r}")

    mean_do = sum(s.dissolved_oxygen_mg_l for s in sample_list) / len(sample_list)
    mean_temp = sum(s.temperature_c for s in sample_list) / len(sample_list)
    mean_turb = sum(s.turbidity_ntu for s in sample_list) / len(sample_list)
    # Salinity not strictly per-species-banded here — out
    # of scope for the MVP signature.

    do_score = _do_safety(mean_do, species)
    temp_score = _temp_safety(mean_temp, species)
    safety = min(do_score, temp_score)

    vision_confidence = _turbidity_to_vision_confidence(mean_turb)

    return WaterChemistryReading(
        safety=max(0.0, min(1.0, safety)),
        vision_confidence=max(0.0, min(1.0, vision_confidence)),
    )

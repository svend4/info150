"""Per-species reference profile for the engine.

Aggregates reference values into a single dataclass for
the engine's escalation decisions. Per-channel band
details live with each signature (gill_rate.py /
water_chemistry.py); this module surfaces engine-level
tuning that varies per species.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import Species


@dataclass(frozen=True)
class AquaticProfile:
    """Engine-level tuning per species."""

    species: Species
    # Overall fused score thresholds.
    overall_urgent: float
    overall_watch: float
    # Per-channel thresholds (used as the alert escalation
    # gates).
    channel_urgent: float
    channel_watch: float


_REGISTRY: dict[Species, AquaticProfile] = {
    "salmon":   AquaticProfile("salmon",   0.50, 0.75, 0.40, 0.65),
    "trout":    AquaticProfile("trout",    0.50, 0.75, 0.40, 0.65),
    "sea_bass": AquaticProfile("sea_bass", 0.45, 0.70, 0.35, 0.60),
    "tilapia":  AquaticProfile("tilapia",  0.45, 0.70, 0.35, 0.60),
    "unknown":  AquaticProfile("unknown",  0.45, 0.70, 0.40, 0.65),
}


def profile_for(species: Species) -> AquaticProfile:
    if species not in _REGISTRY:
        raise KeyError(f"no profile for species {species!r}")
    return _REGISTRY[species]

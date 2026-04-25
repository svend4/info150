"""Per-species acoustic + wingbeat reference bands.

Loose placeholders sourced from the xeno-canto corpus
metadata + standard ornithology references (Sibley Guide,
Birds of the World). Real deployments retrain per
geography — public BirdNET weights cover major regions
but underperform in less-sampled ones (Amazon, Borneo).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import Species


@dataclass(frozen=True)
class AcousticBand:
    """Per-species call-rate + wingbeat reference."""

    species: Species
    typical_calls_per_min: float
    wingbeat_low_hz: float
    wingbeat_high_hz: float


_REGISTRY: dict[Species, AcousticBand] = {
    "mallard":  AcousticBand("mallard",  6,  6,  10),
    "robin":    AcousticBand("robin",   12,  4,   8),
    "sparrow":  AcousticBand("sparrow", 10,  6,  10),
    "raven":    AcousticBand("raven",    4,  3,   5),
    "hawk":     AcousticBand("hawk",     2,  3,   5),
    "finch":    AcousticBand("finch",   14,  6,  10),
    "swift":    AcousticBand("swift",    8, 10,  20),
    "unknown":  AcousticBand("unknown",  6,  4,  12),
}


def band_for(species: Species) -> AcousticBand:
    if species not in _REGISTRY:
        raise KeyError(f"no band for species {species!r}")
    return _REGISTRY[species]

"""Per-terrain scoring profiles.

Each profile captures expected pace bands and fatigue-load
multipliers. Thresholds are stubs drawn from general walking-
guideline references (e.g. American Heart Association on
moderate-intensity walking pace). They are NOT calibrated
against real walkers — treat them as placeholders until a
partnership with a sport-science org lands.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import Terrain


@dataclass(frozen=True)
class TerrainProfile:
    """Scoring / cue thresholds for one terrain."""

    terrain: Terrain
    # Expected pace bands (km/h).
    pace_low: float    # below = "speed_up" advisory
    pace_high: float   # above = "slow_down" advisory
    # How much this terrain weighs into the fatigue index, multiplier 1.0 = baseline.
    fatigue_multiplier: float


FLAT = TerrainProfile(
    terrain="flat",
    pace_low=3.5,
    pace_high=6.0,
    fatigue_multiplier=1.0,
)
HILLY = TerrainProfile(
    terrain="hilly",
    pace_low=2.5,
    pace_high=4.5,
    fatigue_multiplier=1.4,
)
STAIRS = TerrainProfile(
    terrain="stairs",
    pace_low=1.5,
    pace_high=3.0,
    fatigue_multiplier=1.7,
)
MIXED = TerrainProfile(
    terrain="mixed",
    pace_low=3.0,
    pace_high=5.0,
    fatigue_multiplier=1.2,
)


_REGISTRY: dict[Terrain, TerrainProfile] = {
    "flat": FLAT,
    "hilly": HILLY,
    "stairs": STAIRS,
    "mixed": MIXED,
}


def profile_for(terrain: Terrain) -> TerrainProfile:
    if terrain not in _REGISTRY:
        raise KeyError(f"no profile for terrain {terrain!r}")
    return _REGISTRY[terrain]

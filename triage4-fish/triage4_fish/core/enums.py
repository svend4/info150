"""String-literal enums for the aquaculture domain."""

from __future__ import annotations

from typing import Literal


# Species the library has reference bands for. Salmon is
# the dominant aquaculture market; trout / sea bass / tilapia
# round out the major farmed species.
Species = Literal["salmon", "trout", "sea_bass", "tilapia", "unknown"]


WelfareLevel = Literal["steady", "watch", "urgent"]


AlertKind = Literal[
    "gill_rate",
    "school_cohesion",
    "sea_lice",
    "mortality_floor",
    "water_chemistry",
    "calibration",
]


# Water-condition meta — separate from the chemistry sample
# because turbidity is the dominant uncertainty channel
# (parent file risk-flag note).
WaterCondition = Literal["clear", "turbid", "silt_storm"]


VALID_SPECIES: tuple[Species, ...] = (
    "salmon", "trout", "sea_bass", "tilapia", "unknown",
)
VALID_WELFARE_LEVELS: tuple[WelfareLevel, ...] = (
    "steady", "watch", "urgent",
)
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "gill_rate",
    "school_cohesion",
    "sea_lice",
    "mortality_floor",
    "water_chemistry",
    "calibration",
)
VALID_WATER_CONDITIONS: tuple[WaterCondition, ...] = (
    "clear", "turbid", "silt_storm",
)

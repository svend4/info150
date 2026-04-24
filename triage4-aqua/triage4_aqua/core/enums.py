"""String-literal enums for the aquatic-safety domain."""

from __future__ import annotations

from typing import Literal


# Lifeguard-facing alert level.
AlertLevel = Literal["ok", "watch", "urgent"]

# Channel the alert is about.
AlertKind = Literal[
    "submersion",
    "idr",
    "absent",
    "distress",
    "calibration",
]

# Environment conditions that scale engine confidence.
PoolCondition = Literal[
    "clear",
    "turbid",
    "sun_glare",
    "crowded",
]

# Zone kind — drives submersion + presence thresholds.
# Wave pools and lazy rivers have different safe-submersion
# expectations than a lap lane.
WaterZone = Literal[
    "pool",
    "beach",
    "wave_pool",
    "lazy_river",
    "lap_lanes",
]


VALID_ALERT_LEVELS: tuple[AlertLevel, ...] = ("ok", "watch", "urgent")
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "submersion",
    "idr",
    "absent",
    "distress",
    "calibration",
)
VALID_POOL_CONDITIONS: tuple[PoolCondition, ...] = (
    "clear",
    "turbid",
    "sun_glare",
    "crowded",
)
VALID_WATER_ZONES: tuple[WaterZone, ...] = (
    "pool",
    "beach",
    "wave_pool",
    "lazy_river",
    "lap_lanes",
)

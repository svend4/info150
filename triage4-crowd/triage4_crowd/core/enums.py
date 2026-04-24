"""String-literal enums for the crowd-safety domain."""

from __future__ import annotations

from typing import Literal


# Venue-ops facing alert level.
AlertLevel = Literal["ok", "watch", "urgent"]

# What channel the alert is about. "calibration" surfaces
# sensor / upstream data issues.
AlertKind = Literal[
    "density",
    "flow",
    "pressure",
    "medical",
    "calibration",
]

# Zone type — drives which density thresholds apply. A
# transit platform has different safe-density bands than
# a standing concert floor.
ZoneKind = Literal[
    "seating",
    "standing",
    "egress",
    "transit_platform",
    "concourse",
]

# Net direction of flow through the zone. "mixed" means
# directionality is indeterminate; "crossflow" means two
# or more significant directions, which is a design
# problem but not a crush precursor. "in" means net
# inflow — the direction to worry about when density is
# high.
CrowdDirection = Literal[
    "static",
    "in",
    "out",
    "crossflow",
    "mixed",
]


VALID_ALERT_LEVELS: tuple[AlertLevel, ...] = ("ok", "watch", "urgent")
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "density",
    "flow",
    "pressure",
    "medical",
    "calibration",
)
VALID_ZONE_KINDS: tuple[ZoneKind, ...] = (
    "seating",
    "standing",
    "egress",
    "transit_platform",
    "concourse",
)
VALID_CROWD_DIRECTIONS: tuple[CrowdDirection, ...] = (
    "static",
    "in",
    "out",
    "crossflow",
    "mixed",
)

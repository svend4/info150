"""String-literal enums for the coast-safety domain."""

from __future__ import annotations

from typing import Literal


# Operator-facing alert level.
AlertLevel = Literal["ok", "watch", "urgent"]

# What channel the alert is about. "calibration" surfaces
# sensor / upstream data issues.
AlertKind = Literal[
    "density",
    "drowning",
    "sun",
    "lost_child",
    "fall_event",
    "stationary_person",
    "flow_anomaly",
    "slip_risk",
    "calibration",
]

# Zone type along the coast — drives band thresholds.
ZoneKind = Literal[
    "beach",         # sand, sunbathers
    "promenade",     # walkway / boardwalk
    "water",         # swim zone
    "pier",          # narrow strip with railings
]


VALID_ALERT_LEVELS: tuple[AlertLevel, ...] = ("ok", "watch", "urgent")
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "density",
    "drowning",
    "sun",
    "lost_child",
    "fall_event",
    "stationary_person",
    "flow_anomaly",
    "slip_risk",
    "calibration",
)
VALID_ZONE_KINDS: tuple[ZoneKind, ...] = (
    "beach",
    "promenade",
    "water",
    "pier",
)

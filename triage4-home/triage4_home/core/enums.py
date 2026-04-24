"""String-literal enums for the in-home-monitoring domain.

Same `Literal[...]` + plain strings pattern as the other
siblings.
"""

from __future__ import annotations

from typing import Literal


# Caregiver-facing alert level. NOT a clinical severity —
# "urgent" means "caregiver should consider contacting the
# resident or their designated escalation path", NOT "medical
# emergency". The library never initiates 911 itself.
AlertLevel = Literal["ok", "check_in", "urgent"]

# Channel the alert is about. "baseline" fires when the
# per-resident baseline isn't yet established and the engine
# wants to flag lower-confidence scoring.
AlertKind = Literal["fall", "activity", "mobility", "baseline"]

# Rooms the library understands. Anything else the sensor
# hub recognises should be normalised to one of these upstream.
RoomKind = Literal[
    "bedroom",
    "bathroom",
    "kitchen",
    "living",
    "hallway",
    "outside",
]

# Coarse activity buckets for the activity-pattern signature.
# "unknown" is a distinct bucket rather than None because it
# affects the coverage-quality score the engine produces.
ActivityIntensity = Literal["resting", "light", "moderate", "unknown"]


VALID_ALERT_LEVELS: tuple[AlertLevel, ...] = ("ok", "check_in", "urgent")
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "fall",
    "activity",
    "mobility",
    "baseline",
)
VALID_ROOM_KINDS: tuple[RoomKind, ...] = (
    "bedroom",
    "bathroom",
    "kitchen",
    "living",
    "hallway",
    "outside",
)
VALID_INTENSITIES: tuple[ActivityIntensity, ...] = (
    "resting",
    "light",
    "moderate",
    "unknown",
)

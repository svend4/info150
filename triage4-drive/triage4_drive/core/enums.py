"""String-literal enums for the driver-monitoring domain.

Same `Literal[...]` + plain strings pattern as the other
siblings.
"""

from __future__ import annotations

from typing import Literal


# Dispatcher-facing alert level. NOT a clinical severity —
# "critical" means "dispatcher should consider a rest-break
# conversation", not "medical emergency".
AlertLevel = Literal["ok", "caution", "critical"]

# What the alert is about. "calibration" fires when the
# per-session baseline hasn't been learned yet and the engine
# surfaces lower-confidence scores.
AlertKind = Literal[
    "drowsiness",
    "distraction",
    "incapacitation",
    "calibration",
]

# Where the driver is looking. "off_road" is the catch-all
# region that drives the distraction channel.
GazeRegion = Literal[
    "road",
    "left_mirror",
    "right_mirror",
    "rearview_mirror",
    "dashboard",
    "off_road",
]


VALID_ALERT_LEVELS: tuple[AlertLevel, ...] = ("ok", "caution", "critical")
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "drowsiness",
    "distraction",
    "incapacitation",
    "calibration",
)
VALID_GAZE_REGIONS: tuple[GazeRegion, ...] = (
    "road",
    "left_mirror",
    "right_mirror",
    "rearview_mirror",
    "dashboard",
    "off_road",
)

# Gaze regions that count as "on task". Everything else
# accumulates distraction time.
ON_TASK_REGIONS: tuple[GazeRegion, ...] = (
    "road",
    "left_mirror",
    "right_mirror",
    "rearview_mirror",
)

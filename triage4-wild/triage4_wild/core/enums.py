"""String-literal enums for the terrestrial-wildlife domain."""

from __future__ import annotations

from typing import Literal


# Species the library has per-species thresholds for. The
# upstream classifier populates this; unknown species
# fall through to a species-generic default profile.
Species = Literal[
    "elephant",
    "rhino",
    "lion",
    "buffalo",
    "giraffe",
    "zebra",
    "cheetah",
    "unknown",
]


AlertLevel = Literal["ok", "watch", "urgent"]


AlertKind = Literal[
    "gait",
    "thermal",
    "collapse",
    "body_condition",
    "calibration",
]


# Qualitative threat classifier upstream may attach. Used
# by the engine's species-specific red-flag escalation —
# e.g. snare_injury flagged by MegaDetector + visible-
# wire classifier co-firing produces a faster urgent-tier
# escalation than gait alone.
ThreatKind = Literal[
    "snare_injury",
    "thermal_asymmetry",
    "gait_instability",
    "body_condition_low",
    "collapse",
]


CaptureQuality = Literal["good", "partial", "night_ir"]


VALID_SPECIES: tuple[Species, ...] = (
    "elephant",
    "rhino",
    "lion",
    "buffalo",
    "giraffe",
    "zebra",
    "cheetah",
    "unknown",
)
VALID_ALERT_LEVELS: tuple[AlertLevel, ...] = ("ok", "watch", "urgent")
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "gait",
    "thermal",
    "collapse",
    "body_condition",
    "calibration",
)
VALID_THREAT_KINDS: tuple[ThreatKind, ...] = (
    "snare_injury",
    "thermal_asymmetry",
    "gait_instability",
    "body_condition_low",
    "collapse",
)
VALID_CAPTURE_QUALITIES: tuple[CaptureQuality, ...] = (
    "good",
    "partial",
    "night_ir",
)


# SMS-length cap for ranger alerts. Standard Iridium
# satcom / SMS frames tolerate ~160-200 chars; we cap at
# 200 to give consumer apps margin for a short metadata
# prefix.
MAX_RANGER_SMS_CHARS: int = 200

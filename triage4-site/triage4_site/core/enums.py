"""String-literal enums for the site-safety domain."""

from __future__ import annotations

from typing import Literal


# Safety-officer facing alert level. NOT a clinical severity
# and NOT a disciplinary one — "urgent" means "safety officer
# should respond promptly", not "medical emergency" or "HR
# action".
AlertLevel = Literal["ok", "watch", "urgent"]

# Channel the alert is about.
AlertKind = Literal["ppe", "lifting", "heat", "fatigue", "calibration"]

# PPE items the library understands. The sensor hub classifies
# into this enumeration upstream.
PPEItem = Literal["hard_hat", "vest", "harness", "glasses"]

# Site conditions that scale the engine's confidence. These
# are observation-layer artifacts — the engine de-weights
# channels when visibility is poor.
SiteCondition = Literal["clear", "dusty", "rainy", "low_light"]


VALID_ALERT_LEVELS: tuple[AlertLevel, ...] = ("ok", "watch", "urgent")
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "ppe",
    "lifting",
    "heat",
    "fatigue",
    "calibration",
)
VALID_PPE_ITEMS: tuple[PPEItem, ...] = (
    "hard_hat",
    "vest",
    "harness",
    "glasses",
)
VALID_SITE_CONDITIONS: tuple[SiteCondition, ...] = (
    "clear",
    "dusty",
    "rainy",
    "low_light",
)

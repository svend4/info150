"""String-literal enums for the day-walk assistant domain.

No `enum.Enum` — triage4 established the pattern of
`Literal[...]` + plain strings for lightweight serialisation
and test ergonomics, and triage4-stroll follows it.
"""

from __future__ import annotations

from typing import Literal


# Terrain profile for a stroll segment.
Terrain = Literal["flat", "hilly", "stairs", "mixed"]

# Coaching-cue severity. NOT a triage priority.
CueSeverity = Literal["ok", "minor", "severe"]

# Cue category — what the cue is about. Maps to channel scores.
CueKind = Literal["fatigue", "hydration", "shade", "pace", "rest"]

# Pace advisory direction.
PaceAdvisory = Literal["slow_down", "continue", "speed_up"]

VALID_TERRAINS: tuple[Terrain, ...] = ("flat", "hilly", "stairs", "mixed")
VALID_SEVERITIES: tuple[CueSeverity, ...] = ("ok", "minor", "severe")
VALID_CUE_KINDS: tuple[CueKind, ...] = (
    "fatigue", "hydration", "shade", "pace", "rest",
)
VALID_PACE_ADVISORIES: tuple[PaceAdvisory, ...] = (
    "slow_down", "continue", "speed_up",
)

"""String-literal enums for the desk-worker wellness domain.

No `enum.Enum` — triage4 established the pattern of
`Literal[...]` + plain strings for lightweight serialisation
and test ergonomics, and triage4-desk follows it.
"""

from __future__ import annotations

from typing import Literal


# Type of work session — drives band thresholds.
#   office     — meetings + email + light typing, mixed
#   coding     — extended focus, longer Pomodoro blocks acceptable
#   meeting    — relaxed, no microbreak alerts during meetings
#   gaming     — extended sit-and-stare, tight break thresholds
#   streaming  — like gaming + camera-on social pressure on posture
WorkMode = Literal["office", "coding", "meeting", "gaming", "streaming"]

# Coaching-cue severity. NOT a triage priority.
CueSeverity = Literal["ok", "minor", "severe"]

# Cue category — what the cue is about.
CueKind = Literal[
    "fatigue",
    "hydration",
    "eye_strain",
    "posture",
    "microbreak",
    "stretch",
    "drowsiness",
    "distraction",
]

# Posture status the engine emits.
PostureAdvisory = Literal["ok", "slumped", "leaning"]

VALID_WORK_MODES: tuple[WorkMode, ...] = (
    "office", "coding", "meeting", "gaming", "streaming",
)
VALID_SEVERITIES: tuple[CueSeverity, ...] = ("ok", "minor", "severe")
VALID_CUE_KINDS: tuple[CueKind, ...] = (
    "fatigue", "hydration", "eye_strain", "posture",
    "microbreak", "stretch", "drowsiness", "distraction",
)
VALID_POSTURE_ADVISORIES: tuple[PostureAdvisory, ...] = (
    "ok", "slumped", "leaning",
)

"""Per-WorkMode scoring profiles.

Each profile captures expected break-cadence thresholds and a
fatigue multiplier. Thresholds are stubs drawn from general
ergonomic / Pomodoro / 20-20-20 references. They are NOT
calibrated against real users — treat them as placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import WorkMode


@dataclass(frozen=True)
class WorkProfile:
    """Scoring / cue thresholds for one work mode."""

    work_mode: WorkMode
    # Microbreak (Pomodoro) — minutes_since_break above which
    # microbreak_due fires.
    microbreak_minutes: float
    # Stretch / standing break threshold.
    stretch_minutes: float
    # Eye-break (20-20-20) — minutes of continuous screen-staring
    # above which eye_break_due fires.
    eye_break_minutes: float
    # Fatigue multiplier — how aggressively this mode accumulates
    # fatigue. 1.0 = baseline office.
    fatigue_multiplier: float


# Office: standard Pomodoro (25/5), longer block of 90 min for stretch.
OFFICE = WorkProfile(
    work_mode="office",
    microbreak_minutes=25.0,
    stretch_minutes=90.0,
    eye_break_minutes=20.0,
    fatigue_multiplier=1.0,
)

# Coding: longer focus blocks tolerated (50/10), but eye breaks tighter.
CODING = WorkProfile(
    work_mode="coding",
    microbreak_minutes=50.0,
    stretch_minutes=120.0,
    eye_break_minutes=20.0,
    fatigue_multiplier=1.1,
)

# Meeting: relaxed — no microbreak alert during a 60-min meeting,
# but stretch warning still applies.
MEETING = WorkProfile(
    work_mode="meeting",
    microbreak_minutes=60.0,
    stretch_minutes=90.0,
    eye_break_minutes=30.0,
    fatigue_multiplier=0.9,
)

# Gaming: tighter — extended sessions are common but harmful;
# short Pomodoro, aggressive stretch, very tight eye breaks.
GAMING = WorkProfile(
    work_mode="gaming",
    microbreak_minutes=30.0,
    stretch_minutes=60.0,
    eye_break_minutes=15.0,
    fatigue_multiplier=1.4,
)

# Streaming: like gaming + camera-on social pressure on posture.
STREAMING = WorkProfile(
    work_mode="streaming",
    microbreak_minutes=30.0,
    stretch_minutes=60.0,
    eye_break_minutes=15.0,
    fatigue_multiplier=1.5,
)


_REGISTRY: dict[WorkMode, WorkProfile] = {
    "office": OFFICE,
    "coding": CODING,
    "meeting": MEETING,
    "gaming": GAMING,
    "streaming": STREAMING,
}


def profile_for(work_mode: WorkMode) -> WorkProfile:
    if work_mode not in _REGISTRY:
        raise KeyError(f"no profile for work_mode {work_mode!r}")
    return _REGISTRY[work_mode]

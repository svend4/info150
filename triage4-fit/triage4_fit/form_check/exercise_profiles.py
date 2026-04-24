"""Per-exercise scoring profiles.

Each profile captures:
- Expected rep duration band (tempo)
- Depth key joints (for bilateral depth-probe — does the trainee
  hit the bottom of the movement?)
- Specific thresholds for the "minor" and "severe" cue severity
  bands.

Thresholds here are stubs drawn from published form-check
literature (e.g. NSCA Essentials of Personal Training, chapter
15 for squat kinematics). They are NOT calibrated against real
athletes — treat them as placeholders until a partnership with
a coaching org lands.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import ExerciseKind


@dataclass(frozen=True)
class ExerciseProfile:
    """Scoring / cue thresholds for one exercise."""

    exercise: ExerciseKind
    # Expected rep duration band (s). Reps faster than ``tempo_low``
    # trigger "too fast" cues; slower than ``tempo_high`` trigger
    # "too slow" cues (often = failed rep).
    tempo_low: float
    tempo_high: float
    # Symmetry thresholds — below these the engine emits a cue at
    # the named severity.
    minor_symmetry: float
    severe_symmetry: float
    # Depth key joint names. These are the joints whose y-travel
    # within the rep is measured as a depth proxy. Empty tuple
    # means "don't score depth for this exercise".
    depth_joints: tuple[str, ...]
    # Depth-travel thresholds — a depth_joint must travel at least
    # this fraction of the body scale across the rep to count as
    # full-depth (1.0) vs shallow (0.0).
    min_depth_travel: float
    full_depth_travel: float


SQUAT = ExerciseProfile(
    exercise="squat",
    tempo_low=1.5,           # rep should take at least 1.5 s
    tempo_high=6.0,          # > 6 s suggests struggle / stall
    minor_symmetry=0.80,
    severe_symmetry=0.60,
    depth_joints=("hip_l", "hip_r"),
    min_depth_travel=0.10,   # 10 % of body scale = partial squat
    full_depth_travel=0.30,  # 30 % = at-or-below parallel
)

PUSHUP = ExerciseProfile(
    exercise="pushup",
    tempo_low=1.2,
    tempo_high=5.0,
    minor_symmetry=0.80,
    severe_symmetry=0.60,
    depth_joints=("shoulder_l", "shoulder_r"),
    min_depth_travel=0.08,
    full_depth_travel=0.20,
)

DEADLIFT = ExerciseProfile(
    exercise="deadlift",
    tempo_low=1.8,
    tempo_high=6.5,
    minor_symmetry=0.80,
    severe_symmetry=0.60,
    depth_joints=("hip_l", "hip_r"),
    min_depth_travel=0.15,
    full_depth_travel=0.35,
)


_REGISTRY: dict[ExerciseKind, ExerciseProfile] = {
    "squat": SQUAT,
    "pushup": PUSHUP,
    "deadlift": DEADLIFT,
}


def profile_for(exercise: ExerciseKind) -> ExerciseProfile:
    if exercise not in _REGISTRY:
        raise KeyError(f"no profile for exercise {exercise!r}")
    return _REGISTRY[exercise]

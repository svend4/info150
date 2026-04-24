"""Deterministic synthetic session generator for tests + demos.

Parallel in spirit to triage4's ``sim.casualty_profiles`` — it
produces believable inputs to the form engine without needing a
real pose estimator.
"""

from __future__ import annotations

import math
import random
from typing import Iterable

from ..core.enums import ExerciseKind, VALID_EXERCISES
from ..core.models import ExerciseSession, JointPoseSample, RepObservation


# Upright-rest pose in normalised [0, 1] coordinates, side-on camera.
# y grows downward (image convention).
_BASE_POSE: dict[str, tuple[float, float]] = {
    "shoulder_l": (0.45, 0.30),
    "shoulder_r": (0.55, 0.30),
    "elbow_l":    (0.40, 0.45),
    "elbow_r":    (0.60, 0.45),
    "wrist_l":    (0.38, 0.58),
    "wrist_r":    (0.62, 0.58),
    "hip_l":      (0.47, 0.60),
    "hip_r":      (0.53, 0.60),
    "knee_l":     (0.47, 0.75),
    "knee_r":     (0.53, 0.75),
    "ankle_l":    (0.47, 0.90),
    "ankle_r":    (0.53, 0.90),
}


_DEPTH_JOINTS: dict[ExerciseKind, tuple[str, ...]] = {
    "squat": ("hip_l", "hip_r", "knee_l", "knee_r"),
    "pushup": ("shoulder_l", "shoulder_r", "elbow_l", "elbow_r"),
    "deadlift": ("hip_l", "hip_r"),
}


def generate_rep(
    exercise: ExerciseKind,
    rep_index: int,
    duration_s: float = 2.5,
    depth_travel: float = 0.30,
    asymmetry_severity: float = 0.0,
    seed: int = 0,
    n_frames: int = 12,
) -> RepObservation:
    """Build one rep's worth of pose frames + an HR/breathing snapshot.

    ``asymmetry_severity`` in [0, 1] biases the left-side joints
    so the rep's symmetry score degrades predictably — used by
    tests to probe the symmetry threshold, and by demos to make
    cues appear.
    """
    if exercise not in VALID_EXERCISES:
        raise ValueError(f"unknown exercise {exercise!r}")
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    if not 0.0 <= asymmetry_severity <= 1.0:
        raise ValueError("asymmetry_severity must be in [0, 1]")
    if n_frames < 4:
        raise ValueError("n_frames must be >= 4")

    rng = random.Random(seed + rep_index * 1000)
    depth_joints = _DEPTH_JOINTS[exercise]
    samples: list[list[JointPoseSample]] = []

    for i in range(n_frames):
        # u goes 0 → 1 → 0 across the rep (concentric-eccentric).
        t = i / (n_frames - 1)
        u = math.sin(math.pi * t)
        frame: list[JointPoseSample] = []
        for joint, (x, y) in _BASE_POSE.items():
            dy = 0.0
            if joint in depth_joints:
                dy = depth_travel * u
            # Asymmetry — left side travels slightly less than right.
            if asymmetry_severity > 0 and joint.endswith("_l"):
                dy *= max(0.0, 1.0 - asymmetry_severity)
            noise = rng.uniform(-0.005, 0.005)
            frame.append(
                JointPoseSample(
                    joint=joint,
                    x=min(1.0, max(0.0, x + rng.uniform(-0.003, 0.003))),
                    y=min(1.0, max(0.0, y + dy + noise)),
                    confidence=1.0,
                )
            )
        samples.append(frame)

    # HR / breathing rise with intensity (later reps) and
    # decrease with asymmetry (broken form costs more).
    base_hr = 95.0 + 2.5 * rep_index
    base_breathing = 20.0 + 0.8 * rep_index
    hr = base_hr + 6.0 * asymmetry_severity
    breathing = base_breathing + 2.0 * asymmetry_severity

    return RepObservation(
        rep_index=rep_index,
        duration_s=duration_s,
        samples=samples,
        hr_bpm=round(hr, 1),
        breathing_bpm=round(breathing, 1),
    )


def demo_session(
    exercise: ExerciseKind,
    rep_count: int = 5,
    asymmetry_severity: float = 0.2,
    trainee_id: str = "demo_trainee",
    seed: int = 0,
) -> ExerciseSession:
    """Build a full demo session — ramping asymmetry across reps."""
    reps: list[RepObservation] = []
    for i in range(rep_count):
        # Slight fatigue ramp: asymmetry grows with rep_index.
        rep_asym = min(
            1.0, asymmetry_severity * (1.0 + i * 0.25)
        )
        reps.append(
            generate_rep(
                exercise=exercise,
                rep_index=i,
                duration_s=2.5 + 0.15 * i,
                asymmetry_severity=rep_asym,
                seed=seed,
            )
        )
    return ExerciseSession(
        trainee_id=trainee_id,
        exercise=exercise,
        reps=reps,
        reported_rpe=6.0 + 0.5 * rep_count,
    )


# Silence the unused-import warning for the optional ``Iterable``.
_ = Iterable

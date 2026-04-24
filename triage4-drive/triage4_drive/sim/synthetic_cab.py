"""Deterministic synthetic cab-session generator.

Real in-cab driver footage is privacy-sensitive and cannot be
committed to a repo. The engine is exercised against
synthetic ``DriverObservation`` windows tunable across the
three signal axes:

- ``drowsiness``  ∈ [0, 1] — raises PERCLOS and, past ~0.7,
  introduces microsleep runs.
- ``distraction`` ∈ [0, 1] — increases the fraction of time
  gaze spends in "off_road".
- ``incapacitation`` ∈ [0, 1] — introduces a slump-and-hold
  posture pattern in the final portion of the window.

Reproducibility: same ``seed`` always produces the same
observation — critical for test determinism.
"""

from __future__ import annotations

import random

from ..core.enums import GazeRegion
from ..core.models import (
    DriverObservation,
    EyeStateSample,
    GazeSample,
    PostureSample,
)


def generate_observation(
    session_id: str = "sim-session",
    window_duration_s: float = 30.0,
    sample_rate_hz: float = 10.0,
    drowsiness: float = 0.0,
    distraction: float = 0.0,
    incapacitation: float = 0.0,
    seed: int = 0,
) -> DriverObservation:
    """Build one synthetic window of eye / gaze / posture samples."""
    for name, val in (
        ("drowsiness", drowsiness),
        ("distraction", distraction),
        ("incapacitation", incapacitation),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")

    rng = random.Random(hash((session_id, seed)) & 0xFFFFFFFF)
    n_samples = max(2, int(window_duration_s * sample_rate_hz))
    dt = window_duration_s / (n_samples - 1)

    eye_samples: list[EyeStateSample] = []
    gaze_samples: list[GazeSample] = []
    posture_samples: list[PostureSample] = []

    # Pre-decide microsleep intervals — each ~1 s long,
    # triggered only when drowsiness is high.
    microsleep_intervals: list[tuple[float, float]] = []
    if drowsiness >= 0.6:
        # One microsleep per 0.2 units of drowsiness past 0.6.
        n_events = max(1, int((drowsiness - 0.5) * 5))
        for _ in range(n_events):
            start = rng.uniform(0.2, 0.8) * window_duration_s
            duration = rng.uniform(0.8, 1.5)
            microsleep_intervals.append((start, start + duration))

    # Incapacitation slump window — grows from late-start to
    # the end of the window as severity rises.
    slump_start_s = (1.0 - incapacitation) * window_duration_s if incapacitation > 0 else None

    # Distraction "look away" intervals — several short looks
    # at "off_road" that together sum to the target fraction.
    off_task_total_s = distraction * window_duration_s
    off_task_events: list[tuple[float, float]] = []
    remaining = off_task_total_s
    cursor = 0.0
    while remaining > 0.1 and cursor < window_duration_s - 1.0:
        gap = rng.uniform(1.0, 3.0)
        cursor += gap
        if cursor >= window_duration_s:
            break
        dur = min(remaining, rng.uniform(0.5, 2.0))
        off_task_events.append((cursor, cursor + dur))
        cursor += dur
        remaining -= dur

    for i in range(n_samples):
        t = i * dt

        # Eye closure baseline with natural blinks.
        closure = 0.05 + rng.uniform(-0.02, 0.04)
        # Drowsy driving produces bursts of near-closed eyes
        # (heavy eyelids between microsleeps). Each sample has
        # an independent probability proportional to
        # ``drowsiness`` of landing in that "closed" band.
        # Tuned so drowsiness=0.5 produces PERCLOS ≈ 0.25
        # (caution band) and drowsiness=0.85 ≈ 0.4 (critical).
        if drowsiness > 0 and rng.random() < 0.55 * drowsiness:
            closure = 0.85 + rng.uniform(-0.02, 0.1)
        # Microsleep override: inside a microsleep interval,
        # closure is ~1.0.
        for (ms_start, ms_end) in microsleep_intervals:
            if ms_start <= t <= ms_end:
                closure = 0.95 + rng.uniform(-0.05, 0.05)
                break
        closure = max(0.0, min(1.0, closure))
        eye_samples.append(EyeStateSample(t_s=round(t, 4), closure=round(closure, 3)))

        # Gaze region — default road, override during off-task
        # intervals.
        region: GazeRegion = "road"
        for (ot_start, ot_end) in off_task_events:
            if ot_start <= t <= ot_end:
                region = "off_road"
                break
        # Occasional natural mirror glance even in clean driving.
        if region == "road" and rng.random() < 0.05:
            region = rng.choice(["left_mirror", "right_mirror", "rearview_mirror"])
        gaze_samples.append(GazeSample(t_s=round(t, 4), region=region))

        # Posture — upright baseline, override during slump.
        nose_y = 0.30 + rng.uniform(-0.01, 0.01)
        shoulder_y = 0.45 + rng.uniform(-0.01, 0.01)
        if slump_start_s is not None and t >= slump_start_s:
            # Head drops toward / below the shoulders.
            progress = (t - slump_start_s) / max(1e-3, window_duration_s - slump_start_s)
            drop = 0.35 * incapacitation * progress
            nose_y = min(1.0, 0.30 + drop)
        posture_samples.append(PostureSample(
            t_s=round(t, 4),
            nose_y=round(max(0.0, min(1.0, nose_y)), 3),
            shoulder_midline_y=round(max(0.0, min(1.0, shoulder_y)), 3),
        ))

    return DriverObservation(
        session_id=session_id,
        window_duration_s=window_duration_s,
        eye_samples=eye_samples,
        gaze_samples=gaze_samples,
        posture_samples=posture_samples,
    )


def demo_session(
    session_id: str = "DEMO_SESSION",
    seed: int = 0,
) -> list[DriverObservation]:
    """Build a multi-window demo covering every alert level.

    Windows (in order):
    1. Alert baseline — clean driving.
    2. Mild distraction — a few off-road glances.
    3. Drowsiness onset — PERCLOS rises into caution.
    4. Critical drowsiness + microsleep.
    5. Incapacitation candidate — severe slump.
    """
    return [
        generate_observation(
            session_id=f"{session_id}-W1",
            seed=seed,
        ),
        generate_observation(
            session_id=f"{session_id}-W2",
            drowsiness=0.05,
            distraction=0.4,
            seed=seed + 1,
        ),
        generate_observation(
            session_id=f"{session_id}-W3",
            drowsiness=0.5,
            distraction=0.15,
            seed=seed + 2,
        ),
        generate_observation(
            session_id=f"{session_id}-W4",
            drowsiness=0.85,
            distraction=0.2,
            seed=seed + 3,
        ),
        generate_observation(
            session_id=f"{session_id}-W5",
            drowsiness=0.3,
            distraction=0.1,
            incapacitation=0.95,
            seed=seed + 4,
        ),
    ]

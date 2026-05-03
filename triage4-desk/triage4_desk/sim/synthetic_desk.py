"""Deterministic synthetic DeskSession generator."""

from __future__ import annotations

from ..core.enums import VALID_WORK_MODES, WorkMode
from ..core.models import DeskSession


def generate_session(
    worker_id: str = "demo_worker",
    work_mode: WorkMode = "office",
    session_min: float = 35.0,
    minutes_since_break: float = 20.0,
    minutes_since_stretch: float = 60.0,
    typing_intensity: float = 0.4,
    screen_motion_proxy: float = 0.3,
    ambient_light_proxy: float = 0.5,
    posture_quality: float = 0.85,
    drowsiness_signal: float = 0.0,
    distraction_signal: float = 0.0,
    air_temp_c: float | None = 22.0,
    hr_bpm: float | None = 78.0,
) -> DeskSession:
    """Build one synthetic DeskSession."""
    if work_mode not in VALID_WORK_MODES:
        raise ValueError(f"unknown work_mode {work_mode!r}")
    return DeskSession(
        worker_id=worker_id,
        work_mode=work_mode,
        session_min=session_min,
        minutes_since_break=minutes_since_break,
        minutes_since_stretch=minutes_since_stretch,
        typing_intensity=typing_intensity,
        screen_motion_proxy=screen_motion_proxy,
        ambient_light_proxy=ambient_light_proxy,
        posture_quality=posture_quality,
        drowsiness_signal=drowsiness_signal,
        distraction_signal=distraction_signal,
        air_temp_c=air_temp_c,
        hr_bpm=hr_bpm,
    )


def demo_sessions() -> list[DeskSession]:
    """Five-session demo touching the engine's main bands."""
    return [
        generate_session(
            worker_id="W1-fresh", work_mode="office", session_min=10.0,
            minutes_since_break=8.0, minutes_since_stretch=15.0,
            posture_quality=0.95, typing_intensity=0.3,
        ),
        generate_session(
            worker_id="W2-coding", work_mode="coding", session_min=55.0,
            minutes_since_break=40.0, minutes_since_stretch=80.0,
            posture_quality=0.7, typing_intensity=0.7,
            air_temp_c=24.0,
        ),
        generate_session(
            worker_id="W3-meeting", work_mode="meeting", session_min=45.0,
            minutes_since_break=45.0, minutes_since_stretch=70.0,
            posture_quality=0.6, typing_intensity=0.1,
            distraction_signal=0.4,
        ),
        generate_session(
            worker_id="W4-gaming", work_mode="gaming", session_min=120.0,
            minutes_since_break=80.0, minutes_since_stretch=120.0,
            posture_quality=0.4, typing_intensity=0.9,
            screen_motion_proxy=0.85, hr_bpm=110.0,
            ambient_light_proxy=0.15,  # dark room
        ),
        generate_session(
            worker_id="W5-late-coder", work_mode="coding", session_min=200.0,
            minutes_since_break=70.0, minutes_since_stretch=200.0,
            posture_quality=0.35, typing_intensity=0.4,
            drowsiness_signal=0.8, hr_bpm=58.0,
            ambient_light_proxy=0.20,
        ),
    ]


def demo_session(
    work_mode: WorkMode = "office",
    session_min: float = 35.0,
    posture_quality: float = 0.7,
) -> DeskSession:
    """Single-session demo (ergonomic)."""
    return generate_session(
        work_mode=work_mode,
        session_min=session_min,
        posture_quality=posture_quality,
    )

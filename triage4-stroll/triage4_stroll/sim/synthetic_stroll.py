"""Deterministic synthetic stroll-segment generator.

Produces believable :class:`StrollSegment` inputs without
needing real GPS or camera data.
"""

from __future__ import annotations

from ..core.enums import Terrain, VALID_TERRAINS
from ..core.models import StrollSegment


def generate_segment(
    walker_id: str = "demo_walker",
    terrain: Terrain = "flat",
    duration_min: float = 25.0,
    pace_kmh: float = 4.5,
    activity_intensity: float = 0.45,
    sun_exposure_proxy: float = 0.4,
    minutes_since_rest: float = 25.0,
    air_temp_c: float | None = 24.0,
    hr_bpm: float | None = 110.0,
) -> StrollSegment:
    """Build one synthetic walk segment."""
    if terrain not in VALID_TERRAINS:
        raise ValueError(f"unknown terrain {terrain!r}")
    return StrollSegment(
        walker_id=walker_id,
        terrain=terrain,
        pace_kmh=pace_kmh,
        duration_min=duration_min,
        activity_intensity=activity_intensity,
        sun_exposure_proxy=sun_exposure_proxy,
        minutes_since_rest=minutes_since_rest,
        air_temp_c=air_temp_c,
        hr_bpm=hr_bpm,
    )


def demo_segments() -> list[StrollSegment]:
    """Five-segment demo touching the engine's main bands."""
    return [
        generate_segment(
            walker_id="W1-fresh", terrain="flat", duration_min=10.0,
            pace_kmh=4.0, activity_intensity=0.3, sun_exposure_proxy=0.25,
            minutes_since_rest=10.0, air_temp_c=20.0, hr_bpm=98.0,
        ),
        generate_segment(
            walker_id="W2-park", terrain="mixed", duration_min=35.0,
            pace_kmh=4.6, activity_intensity=0.5, sun_exposure_proxy=0.55,
            minutes_since_rest=22.0, air_temp_c=24.0, hr_bpm=118.0,
        ),
        generate_segment(
            walker_id="W3-hill", terrain="hilly", duration_min=45.0,
            pace_kmh=3.2, activity_intensity=0.7, sun_exposure_proxy=0.7,
            minutes_since_rest=35.0, air_temp_c=26.0, hr_bpm=140.0,
        ),
        generate_segment(
            walker_id="W4-stairs", terrain="stairs", duration_min=20.0,
            pace_kmh=2.4, activity_intensity=0.85, sun_exposure_proxy=0.2,
            minutes_since_rest=18.0, air_temp_c=22.0, hr_bpm=155.0,
        ),
        generate_segment(
            walker_id="W5-spent", terrain="flat", duration_min=80.0,
            pace_kmh=2.5, activity_intensity=0.4, sun_exposure_proxy=0.85,
            minutes_since_rest=55.0, air_temp_c=29.0, hr_bpm=145.0,
        ),
    ]


def demo_segment(
    terrain: Terrain = "flat",
    duration_min: float = 25.0,
    activity_intensity: float = 0.45,
    sun_exposure_proxy: float = 0.4,
) -> StrollSegment:
    """Single-segment demo (back-compat ergonomic)."""
    return generate_segment(
        terrain=terrain,
        duration_min=duration_min,
        activity_intensity=activity_intensity,
        sun_exposure_proxy=sun_exposure_proxy,
    )

"""Deterministic synthetic swimmer-observation generator.

Real drowning footage cannot be ethically or legally gathered
at scale. The library is exercised against synthetic
``SwimmerObservation`` windows tunable across the four
signal axes:

- ``submersion_s``   ∈ [0, 120] — inject a submersion run of
  this many seconds.
- ``idr_severity``   ∈ [0, 1] — how many surface samples
  show the IDR pattern.
- ``absence_s``      ∈ [0, 120] — simulate a presence gap of
  this many seconds.
- ``distress_level`` ∈ [0, 1] — fraction of surface samples
  with a low head-height reading.

Seeds use ``zlib.crc32`` for cross-run stability.
"""

from __future__ import annotations

import random
import zlib

from ..core.enums import PoolCondition, WaterZone
from ..core.models import (
    SubmersionSample,
    SurfacePoseSample,
    SwimmerObservation,
    SwimmerPresenceSample,
)


_DEFAULT_WINDOW_S = 60.0
_SURFACE_INTERVAL_S = 1.0
_SUBMERSION_INTERVAL_S = 0.5
_PRESENCE_INTERVAL_S = 2.0


def _rng(seed_source: tuple[str, int]) -> random.Random:
    seed_bytes = f"{seed_source[0]}|{seed_source[1]}".encode("utf-8")
    return random.Random(zlib.crc32(seed_bytes))


def generate_observation(
    swimmer_token: str = "S-001",
    zone: WaterZone = "pool",
    window_duration_s: float = _DEFAULT_WINDOW_S,
    submersion_s: float = 0.0,
    idr_severity: float = 0.0,
    absence_s: float = 0.0,
    distress_level: float = 0.0,
    pool_condition: PoolCondition = "clear",
    seed: int = 0,
) -> SwimmerObservation:
    """Build one synthetic swimmer observation window."""
    for name, val in (
        ("idr_severity", idr_severity),
        ("distress_level", distress_level),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if submersion_s < 0 or submersion_s > 300:
        raise ValueError(
            f"submersion_s out of plausible range, got {submersion_s}"
        )
    if absence_s < 0 or absence_s > 300:
        raise ValueError(
            f"absence_s out of plausible range, got {absence_s}"
        )
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")

    rng = _rng((swimmer_token, seed))

    # --- Submersion samples ---
    submersion_samples: list[SubmersionSample] = []
    n_sub = max(4, int(window_duration_s / _SUBMERSION_INTERVAL_S))
    dt_sub = window_duration_s / (n_sub - 1)
    # Position the submersion run in the middle of the window.
    sub_start = max(0.0, (window_duration_s - submersion_s) / 2.0)
    sub_end = sub_start + submersion_s
    for i in range(n_sub):
        t = i * dt_sub
        submersion_samples.append(SubmersionSample(
            t_s=round(t, 3),
            submerged=(sub_start <= t <= sub_end) and submersion_s > 0,
        ))

    # --- Surface-pose samples ---
    surface_samples: list[SurfacePoseSample] = []
    n_surf = max(4, int(window_duration_s / _SURFACE_INTERVAL_S))
    dt_surf = window_duration_s / (n_surf - 1)
    for i in range(n_surf):
        t = i * dt_surf
        # IDR pattern with probability idr_severity.
        is_idr = rng.random() < idr_severity
        is_distress = rng.random() < distress_level and not is_idr
        if is_idr:
            head = 0.20 + rng.uniform(-0.05, 0.05)
            vert = 0.85 + rng.uniform(-0.05, 0.05)
            rhythm = 0.15 + rng.uniform(-0.05, 0.05)
        elif is_distress:
            head = 0.20 + rng.uniform(-0.05, 0.05)
            vert = 0.40 + rng.uniform(-0.05, 0.05)
            rhythm = 0.50 + rng.uniform(-0.05, 0.05)
        else:
            # Normal swimming.
            head = 0.70 + rng.uniform(-0.1, 0.1)
            vert = 0.25 + rng.uniform(-0.1, 0.1)
            rhythm = 0.80 + rng.uniform(-0.1, 0.1)
        surface_samples.append(SurfacePoseSample(
            t_s=round(t, 3),
            head_height_rel=round(max(0.0, min(1.0, head)), 3),
            body_vertical=round(max(0.0, min(1.0, vert)), 3),
            motion_rhythm=round(max(0.0, min(1.0, rhythm)), 3),
        ))

    # --- Presence heartbeats ---
    presence_samples: list[SwimmerPresenceSample] = []
    n_pres = max(4, int(window_duration_s / _PRESENCE_INTERVAL_S))
    dt_pres = window_duration_s / (n_pres - 1)
    # Absence window mid-sample.
    abs_start = max(0.0, (window_duration_s - absence_s) / 2.0)
    abs_end = abs_start + absence_s
    for i in range(n_pres):
        t = i * dt_pres
        active = not ((abs_start <= t <= abs_end) and absence_s > 0)
        presence_samples.append(SwimmerPresenceSample(
            t_s=round(t, 3),
            active=active,
        ))

    return SwimmerObservation(
        swimmer_token=swimmer_token,
        zone=zone,
        window_duration_s=window_duration_s,
        surface_samples=surface_samples,
        submersion_samples=submersion_samples,
        presence_samples=presence_samples,
        pool_condition=pool_condition,
    )


def demo_pool() -> list[SwimmerObservation]:
    """Five-swimmer demo covering each channel's bands.

    1. Calm lap swimmer — baseline.
    2. Swimmer submersion approaching the watch band.
    3. Full IDR pattern — urgent.
    4. Absent swimmer — urgent.
    5. Submersion + distress — urgent (multi-channel).
    """
    return [
        generate_observation(
            swimmer_token="S-001", zone="lap_lanes", seed=1,
        ),
        generate_observation(
            swimmer_token="S-002", zone="pool",
            submersion_s=20.0, seed=2,
        ),
        generate_observation(
            swimmer_token="S-003", zone="pool",
            idr_severity=0.8, seed=3,
        ),
        generate_observation(
            swimmer_token="S-004", zone="wave_pool",
            absence_s=50.0, seed=4,
        ),
        generate_observation(
            swimmer_token="S-005", zone="pool",
            submersion_s=40.0, distress_level=0.6, seed=5,
        ),
    ]

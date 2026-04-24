"""Deterministic synthetic shift generator.

Real site footage is NDA-locked and privacy-sensitive;
committing any to the repo would cross the privacy boundary.
The engine is exercised against synthetic
``WorkerObservation`` windows tunable across the four signal
axes:

- ``ppe_compliance``     ∈ [0, 1] — fraction of samples where
  every required item is present. Defaults to 1.0
  (compliant).
- ``unsafe_lifting``     ∈ [0, 1] — scales the peak back-angle
  at load into the unsafe band.
- ``heat_stress``        ∈ [0, 1] — elevates skin temp and
  ambient toward the heat-stress bands.
- ``fatigue``            ∈ [0, 1] — drives the late-shift pace
  down and asymmetry up relative to early shift.

Seeds use ``zlib.crc32`` for reproducibility across runs
(PYTHONHASHSEED would randomise builtin hash()).
"""

from __future__ import annotations

import random
import zlib

from ..core.enums import PPEItem, SiteCondition
from ..core.models import (
    FatigueGaitSample,
    LiftingSample,
    PPESample,
    ThermalSample,
    WorkerObservation,
)


_DEFAULT_WINDOW_S = 2.0 * 3600.0  # two-hour pass
_PPE_SAMPLE_INTERVAL_S = 60.0     # one PPE frame per minute
_GAIT_SAMPLE_INTERVAL_S = 300.0   # one gait window per 5 min
_THERMAL_SAMPLE_INTERVAL_S = 300.0
_LIFT_COUNT_PER_WINDOW = 20       # one lift every ~6 minutes


_DEFAULT_REQUIRED_PPE: tuple[PPEItem, ...] = (
    "hard_hat", "vest", "harness",
)


def _rng(seed_source: tuple[str, int]) -> random.Random:
    seed_bytes = f"{seed_source[0]}|{seed_source[1]}".encode("utf-8")
    return random.Random(zlib.crc32(seed_bytes))


def generate_observation(
    worker_token: str = "W-000",
    window_duration_s: float = _DEFAULT_WINDOW_S,
    required_ppe: tuple[PPEItem, ...] = _DEFAULT_REQUIRED_PPE,
    ppe_compliance: float = 1.0,
    unsafe_lifting: float = 0.0,
    heat_stress: float = 0.0,
    fatigue: float = 0.0,
    site_condition: SiteCondition = "clear",
    seed: int = 0,
) -> WorkerObservation:
    """Build one worker's observation window."""
    for name, val in (
        ("ppe_compliance", ppe_compliance),
        ("unsafe_lifting", unsafe_lifting),
        ("heat_stress", heat_stress),
        ("fatigue", fatigue),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")

    rng = _rng((worker_token, seed))

    # --- PPE samples ---
    ppe_samples: list[PPESample] = []
    n_ppe = max(2, int(window_duration_s / _PPE_SAMPLE_INTERVAL_S))
    for i in range(n_ppe):
        t = i * (window_duration_s / (n_ppe - 1))
        # With probability ``ppe_compliance``, every required
        # item is detected. Otherwise one required item is
        # dropped at random.
        if rng.random() < ppe_compliance:
            items = required_ppe
        else:
            # Drop one required item.
            missing_idx = rng.randrange(len(required_ppe)) if required_ppe else 0
            items = tuple(
                it for i2, it in enumerate(required_ppe) if i2 != missing_idx
            ) if required_ppe else ()
        ppe_samples.append(PPESample(
            t_s=round(t, 3),
            items_detected=items,
        ))

    # --- Lifting samples ---
    lifting_samples: list[LiftingSample] = []
    for i in range(_LIFT_COUNT_PER_WINDOW):
        t = (i + 0.5) * (window_duration_s / _LIFT_COUNT_PER_WINDOW)
        # Unsafe-lifting dial pushes the back angle from ~25°
        # (safe) toward ~70° (clearly unsafe).
        base_angle = 25.0 + 45.0 * unsafe_lifting
        back_angle = base_angle + rng.uniform(-5.0, 5.0)
        load = max(0.0, 15.0 + rng.uniform(-5.0, 5.0))
        lifting_samples.append(LiftingSample(
            t_s=round(t, 3),
            back_angle_deg=round(max(0.0, min(180.0, back_angle)), 2),
            load_kg=round(load, 1),
        ))

    # --- Thermal samples ---
    thermal_samples: list[ThermalSample] = []
    n_thermal = max(2, int(window_duration_s / _THERMAL_SAMPLE_INTERVAL_S))
    for i in range(n_thermal):
        t = i * (window_duration_s / (n_thermal - 1))
        # Resting skin ~33.5 °C, rising with heat_stress.
        skin = 33.5 + 5.5 * heat_stress + rng.uniform(-0.3, 0.3)
        # Ambient: 22 °C baseline, rising with heat_stress to ~38 °C.
        ambient = 22.0 + 16.0 * heat_stress + rng.uniform(-0.5, 0.5)
        thermal_samples.append(ThermalSample(
            t_s=round(t, 3),
            skin_temp_c=round(min(44.9, max(20.1, skin)), 2),
            ambient_temp_c=round(min(54.9, max(-29.9, ambient)), 2),
        ))

    # --- Fatigue-gait samples ---
    gait_samples: list[FatigueGaitSample] = []
    n_gait = max(6, int(window_duration_s / _GAIT_SAMPLE_INTERVAL_S))
    early_pace_mps = 1.25
    # Late-shift pace drops with fatigue up to 40 %.
    late_pace_mps = early_pace_mps * (1.0 - 0.4 * fatigue)
    for i in range(n_gait):
        t = i * (window_duration_s / (n_gait - 1))
        progress = i / (n_gait - 1)
        pace = early_pace_mps + (late_pace_mps - early_pace_mps) * progress
        pace += rng.uniform(-0.05, 0.05)
        pace = max(0.1, min(2.0, pace))
        # Asymmetry grows with fatigue late in the shift.
        asymmetry = 0.05 + 0.35 * fatigue * progress
        asymmetry += rng.uniform(-0.02, 0.02)
        asymmetry = max(0.0, min(1.0, asymmetry))
        gait_samples.append(FatigueGaitSample(
            t_s=round(t, 3),
            pace_mps=round(pace, 3),
            asymmetry=round(asymmetry, 3),
        ))

    return WorkerObservation(
        worker_token=worker_token,
        window_duration_s=window_duration_s,
        required_ppe=required_ppe,
        ppe_samples=ppe_samples,
        lifting_samples=lifting_samples,
        thermal_samples=thermal_samples,
        gait_samples=gait_samples,
        site_condition=site_condition,
    )


def demo_shift() -> list[WorkerObservation]:
    """Five-observation demo covering each channel's alert bands.

    1. Baseline — compliant, safe, cool, fresh.
    2. PPE gap — below watch threshold.
    3. Unsafe lifting — into urgent band.
    4. Heat stress — into urgent band.
    5. Late-shift fatigue — into urgent band.
    """
    return [
        generate_observation(worker_token="W-001", seed=1),
        generate_observation(
            worker_token="W-002", ppe_compliance=0.75, seed=2,
        ),
        generate_observation(
            worker_token="W-003", unsafe_lifting=0.85, seed=3,
        ),
        generate_observation(
            worker_token="W-004", heat_stress=0.85, seed=4,
        ),
        generate_observation(
            worker_token="W-005", fatigue=0.85, seed=5,
        ),
    ]

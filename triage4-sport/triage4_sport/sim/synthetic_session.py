"""Deterministic synthetic athlete-session generator.

Real elite-athlete tracking data is partner-team-protected
under league CBAs. Library is exercised against synthetic
``AthleteObservation`` records.

Seeds use ``zlib.crc32`` for cross-run stability.
"""

from __future__ import annotations

import random
import zlib
from typing import cast

from ..core.enums import MovementKind, Sport
from ..core.models import (
    AthleteBaseline,
    AthleteObservation,
    MovementSample,
    RecoveryHRSample,
    WorkloadSample,
)


_DEFAULT_SESSION_S = 90 * 60  # 90-minute training session


def _rng(seed_source: tuple[str, int]) -> random.Random:
    seed_bytes = f"{seed_source[0]}|{seed_source[1]}".encode("utf-8")
    return random.Random(zlib.crc32(seed_bytes))


def generate_observation(
    athlete_token: str = "A-001",
    sport: Sport = "soccer",
    session_duration_s: float = _DEFAULT_SESSION_S,
    form_asymmetry: float = 0.15,
    workload_intensity: float = 0.45,
    recovery_drop_bpm: float = 32.0,
    seed: int = 0,
) -> AthleteObservation:
    """Build one synthetic AthleteObservation."""
    if not 0.0 <= form_asymmetry <= 1.0:
        raise ValueError(
            f"form_asymmetry must be in [0, 1], got {form_asymmetry}"
        )
    if not 0.0 <= workload_intensity <= 1.0:
        raise ValueError(
            f"workload_intensity must be in [0, 1], got {workload_intensity}"
        )
    if not 0.0 <= recovery_drop_bpm <= 100.0:
        raise ValueError(
            f"recovery_drop_bpm out of range, got {recovery_drop_bpm}"
        )
    if session_duration_s <= 0:
        raise ValueError("session_duration_s must be positive")

    rng = _rng((athlete_token, seed))

    # --- Movement samples ---
    movement_samples: list[MovementSample] = []
    n_movements = max(5, int(session_duration_s / 300))  # one every 5 min
    sport_movement: MovementKind = cast(MovementKind, {
        "soccer":     "kick",
        "basketball": "jump",
        "tennis":     "serve",
        "baseball":   "throw",
        "sprint":     "stride",
        "swim":       "stroke",
        "general":    "general",
    }[sport])
    for i in range(n_movements):
        t = i * (session_duration_s / (n_movements - 1)) if n_movements > 1 else 0.0
        asym = max(0.0, min(1.0,
            form_asymmetry + rng.uniform(-0.05, 0.05),
        ))
        rom = max(0.0, min(1.0, 0.85 - asym * 0.4 + rng.uniform(-0.05, 0.05)))
        movement_samples.append(MovementSample(
            t_s=round(t, 3),
            kind=sport_movement,
            form_asymmetry=round(asym, 3),
            range_of_motion=round(rom, 3),
        ))

    # --- Workload samples (one summary per session) ---
    distance = max(0.0, min(30000.0, 6000.0 + workload_intensity * 8000.0))
    sprints = max(0, min(1000, int(40 + workload_intensity * 130)))
    accels = max(0, min(1000, int(80 + workload_intensity * 140)))
    decels = max(0, min(1000, int(80 + workload_intensity * 140)))
    workload_samples = [WorkloadSample(
        t_s=round(session_duration_s, 3),
        distance_m=round(distance, 1),
        high_speed_runs=sprints,
        accelerations=accels,
        decelerations=decels,
    )]

    # --- Recovery samples ---
    n_recovery = 4
    recovery_samples: list[RecoveryHRSample] = []
    for i in range(n_recovery):
        t = (i + 1) * (session_duration_s / (n_recovery + 1))
        peak = 165.0 + rng.uniform(-10.0, 15.0)
        drop = recovery_drop_bpm + rng.uniform(-3.0, 3.0)
        recovery_samples.append(RecoveryHRSample(
            t_s=round(t, 3),
            peak_hr_bpm=round(min(250.0, max(60.0, peak)), 2),
            recovery_drop_bpm=round(max(0.0, min(100.0, drop)), 2),
        ))

    return AthleteObservation(
        athlete_token=athlete_token,
        sport=sport,
        session_duration_s=session_duration_s,
        movement_samples=movement_samples,
        workload_samples=workload_samples,
        recovery_samples=recovery_samples,
    )


def demo_baseline() -> AthleteBaseline:
    """Synthetic athlete-baseline matching the demo
    observations' typical values."""
    return AthleteBaseline(
        typical_form_asymmetry=0.15,
        typical_workload_index=0.50,
        typical_recovery_drop_bpm=32.0,
    )


def demo_sessions() -> list[AthleteObservation]:
    """Five demo sessions exercising each tier.

    1. Steady — at-baseline session.
    2. Form asymmetry trending up → monitor.
    3. Workload spike → trainer hold note.
    4. Multi-channel deviation → physician alert path.
    5. Recovery HR poor → trainer hold note.
    """
    return [
        # Steady at-baseline session — minimal workload
        # intensity to keep the normalised index below the
        # 0.50 baseline.
        generate_observation(
            athlete_token="A-001", sport="soccer",
            workload_intensity=0.10, seed=1,
        ),
        # Form asymmetry drifts above baseline → trainer note
        # only (single-channel watch-band signal doesn't tip the
        # overall risk_band to monitor — coach stays unalerted).
        generate_observation(
            athlete_token="A-002", sport="soccer",
            form_asymmetry=0.28, workload_intensity=0.10,
            seed=2,
        ),
        # Multi-channel mid-band — overall lands in 'monitor'.
        # Single-channel signals don't reach 'monitor' alone;
        # two co-deviating channels do.
        generate_observation(
            athlete_token="A-003", sport="soccer",
            form_asymmetry=0.25, workload_intensity=0.35,
            seed=3,
        ),
        # Multi-channel deviation → physician alert path.
        generate_observation(
            athlete_token="A-004", sport="soccer",
            form_asymmetry=0.55, workload_intensity=0.85,
            recovery_drop_bpm=14.0, seed=4,
        ),
        # Recovery HR poor — single-channel hold via recovery.
        generate_observation(
            athlete_token="A-005", sport="soccer",
            workload_intensity=0.10, recovery_drop_bpm=10.0,
            seed=5,
        ),
    ]

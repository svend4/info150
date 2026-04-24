"""Deterministic synthetic one-day home-observation generator.

Real in-home resident footage is one of the most privacy-
sensitive data categories there is — committing any to the
repo would cross the privacy boundary before the code even
runs. The engine is exercised against synthetic
``ResidentObservation`` windows tunable across the three
signal axes:

- ``fall_event``    — if True, inject a 3 g impact with an
  8 s stillness window somewhere in the day.
- ``activity_deviation`` ∈ [0, 1] — increases time spent in
  "resting" relative to baseline.
- ``mobility_decline`` ∈ [0, 1] — slows the per-transition
  pace by a proportional factor.

Reproducibility: same ``seed`` produces the same observation.
"""

from __future__ import annotations

import random

from ..core.enums import ActivityIntensity, RoomKind
from ..core.models import (
    ActivitySample,
    ImpactSample,
    ResidentObservation,
    RoomTransition,
)
from ..home_monitor.monitoring_engine import ResidentBaseline
from ..signatures.activity_pattern import ActivityFractions


# 16-hour daylight observation window — 08:00 to 24:00 local.
_DAY_DURATION_S = 16.0 * 3600
_ACTIVITY_SAMPLE_INTERVAL_S = 900.0  # 15 min

# Typical room-to-room distances in a small single-storey home.
_ROOM_DISTANCES: dict[tuple[RoomKind, RoomKind], float] = {
    ("bedroom", "hallway"):  3.0,
    ("hallway", "bedroom"):  3.0,
    ("hallway", "bathroom"): 2.0,
    ("bathroom", "hallway"): 2.0,
    ("hallway", "kitchen"):  4.0,
    ("kitchen", "hallway"):  4.0,
    ("hallway", "living"):   2.5,
    ("living", "hallway"):   2.5,
    ("living", "kitchen"):   6.0,
    ("kitchen", "living"):   6.0,
    ("bedroom", "bathroom"): 5.0,
    ("bathroom", "bedroom"): 5.0,
}


def _distance(from_room: RoomKind, to_room: RoomKind) -> float:
    """Look up a typical path length for the room pair."""
    key = (from_room, to_room)
    if key in _ROOM_DISTANCES:
        return _ROOM_DISTANCES[key]
    return 4.0  # conservative default for unmapped pairs


def _scripted_route() -> list[tuple[RoomKind, RoomKind]]:
    """A reasonable one-day route through the home."""
    return [
        ("bedroom", "hallway"),
        ("hallway", "bathroom"),
        ("bathroom", "hallway"),
        ("hallway", "kitchen"),
        ("kitchen", "living"),
        ("living", "hallway"),
        ("hallway", "bathroom"),
        ("bathroom", "hallway"),
        ("hallway", "kitchen"),
        ("kitchen", "living"),
        ("living", "hallway"),
        ("hallway", "bedroom"),
    ]


def generate_observation(
    window_id: str = "DAY",
    window_duration_s: float = _DAY_DURATION_S,
    fall_event: bool = False,
    activity_deviation: float = 0.0,
    mobility_decline: float = 0.0,
    baseline_pace_mps: float = 0.9,
    seed: int = 0,
) -> ResidentObservation:
    """Build one synthetic day of home observations."""
    for name, val in (
        ("activity_deviation", activity_deviation),
        ("mobility_decline", mobility_decline),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")

    rng = random.Random(hash((window_id, seed)) & 0xFFFFFFFF)

    # --- Activity samples ---
    # Base day has ~35 % resting / ~45 % light / ~20 % moderate.
    # activity_deviation shifts mass toward resting.
    activity_samples: list[ActivitySample] = []
    n_samples = max(2, int(window_duration_s / _ACTIVITY_SAMPLE_INTERVAL_S))
    for i in range(n_samples):
        t = i * (window_duration_s / (n_samples - 1))
        r = rng.random()
        # Threshold boundaries shift with deviation.
        resting_cap = 0.35 + 0.50 * activity_deviation
        light_cap = resting_cap + 0.45 * (1.0 - activity_deviation * 0.5)
        if r < resting_cap:
            intensity: ActivityIntensity = "resting"
        elif r < light_cap:
            intensity = "light"
        else:
            intensity = "moderate"
        activity_samples.append(
            ActivitySample(t_s=round(t, 3), intensity=intensity)
        )

    # --- Room transitions ---
    route = _scripted_route()
    transitions: list[RoomTransition] = []
    step = window_duration_s / (len(route) + 1)
    # Per-transition pace slows with mobility_decline.
    slowdown = 1.0 + 2.0 * mobility_decline
    for i, (from_room, to_room) in enumerate(route):
        jitter = rng.uniform(-step * 0.15, step * 0.15)
        t_s = (i + 1) * step + jitter
        dist = _distance(from_room, to_room)
        # Transit time = distance / pace, with ± 15 % noise.
        transit_s = (dist / baseline_pace_mps) * slowdown
        transit_s *= rng.uniform(0.85, 1.15)
        transitions.append(RoomTransition(
            t_s=round(t_s, 3),
            from_room=from_room,
            to_room=to_room,
            distance_m=dist,
            duration_s=round(max(0.5, transit_s), 3),
        ))

    # --- Impact samples ---
    impacts: list[ImpactSample] = []
    if fall_event:
        t_fall = window_duration_s * rng.uniform(0.3, 0.7)
        impacts.append(ImpactSample(
            t_s=round(t_fall, 3),
            magnitude_g=3.0 + rng.uniform(0, 0.8),
            stillness_after_s=10.0 + rng.uniform(0, 5),
        ))

    return ResidentObservation(
        window_id=window_id,
        window_duration_s=window_duration_s,
        impacts=impacts,
        activity_samples=activity_samples,
        transitions=transitions,
    )


def demo_baseline() -> ResidentBaseline:
    """Canonical baseline a consumer app might learn over a week.

    Values chosen so the demo windows below surface the
    expected alert bands.
    """
    return ResidentBaseline(
        activity=ActivityFractions(
            resting=0.35, light=0.45, moderate=0.20,
        ),
        mobility_median_mps=0.9,
    )


def demo_day_series() -> list[ResidentObservation]:
    """Five-day progression covering every alert band.

    1. Routine day — everything aligned.
    2. Light activity deviation — routine change.
    3. Strong activity deviation — caregiver check-in.
    4. Mobility decline.
    5. Fall candidate.
    """
    return [
        generate_observation(
            window_id="DAY_1", seed=1,
        ),
        generate_observation(
            window_id="DAY_2", activity_deviation=0.3, seed=2,
        ),
        generate_observation(
            window_id="DAY_3", activity_deviation=0.95, seed=3,
        ),
        generate_observation(
            window_id="DAY_4", mobility_decline=0.40, seed=4,
        ),
        generate_observation(
            window_id="DAY_5", fall_event=True, seed=5,
        ),
    ]

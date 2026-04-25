"""Deterministic synthetic station-pass generator.

Real reserve / migration-corridor recordings are
partnership-protected. The library is exercised against
synthetic ``BirdObservation`` records.

Seeds use ``zlib.crc32`` for cross-run stability.
"""

from __future__ import annotations

import random

from biocore.seeds import crc32_seed

from ..core.enums import CallKind, Species
from ..core.models import (
    BirdObservation,
    BodyThermalSample,
    CallSample,
    DeadBirdCandidate,
    WingbeatSample,
)


_DEFAULT_WINDOW_S = 60.0


def _rng(seed_source: tuple[str, int]) -> random.Random:
    """Build a deterministic RNG for the seed-source tuple.

    Delegates to ``biocore.seeds.crc32_seed`` (extracted in
    biocore tier-1).
    """
    return random.Random(crc32_seed(*seed_source))


def generate_observation(
    obs_token: str = "OBS-001",
    station_id: str = "station-A",
    location_handle: str = "grid-1",
    expected_species: tuple[Species, ...] = ("robin", "sparrow", "finch"),
    window_duration_s: float = _DEFAULT_WINDOW_S,
    expected_species_present_fraction: float = 1.0,
    distress_fraction: float = 0.0,
    wingbeat_anomaly: float = 0.0,
    thermal_elevation: float = 0.0,
    dead_bird_count: int = 0,
    seed: int = 0,
) -> BirdObservation:
    """Build one synthetic BirdObservation."""
    for name, val in (
        ("expected_species_present_fraction", expected_species_present_fraction),
        ("distress_fraction", distress_fraction),
        ("wingbeat_anomaly", wingbeat_anomaly),
        ("thermal_elevation", thermal_elevation),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if dead_bird_count < 0 or dead_bird_count > 50:
        raise ValueError(
            f"dead_bird_count must be in [0, 50], got {dead_bird_count}"
        )
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")

    rng = _rng((obs_token, seed))

    # --- Call samples ---
    call_samples: list[CallSample] = []
    # Randomly emit calls during the window.
    n_calls = max(0, int(window_duration_s / 5.0))  # ~12 calls per minute
    expected_count = int(len(expected_species) *
                         expected_species_present_fraction)
    present = list(expected_species[:expected_count])
    if not present:
        # Caller asked for zero expected-species presence —
        # synthetic emits 'unknown' calls so the window
        # isn't empty, but they don't satisfy the
        # call_presence expectation list.
        present = ["unknown"]
    for i in range(n_calls):
        t = (i + rng.random()) * (window_duration_s / max(1, n_calls))
        species = present[i % len(present)]
        # distress_fraction governs the kind distribution.
        is_distress = rng.random() < distress_fraction
        kind: CallKind = "distress" if is_distress else (
            ["song", "chip", "alarm"][i % 3]  # type: ignore[assignment]
        )
        conf = 0.6 + rng.uniform(-0.1, 0.3)
        call_samples.append(CallSample(
            t_s=round(t, 3),
            species=species,
            kind=kind,
            confidence=round(max(0.0, min(1.0, conf)), 3),
        ))

    # --- Wingbeat samples (every 6 s when birds are seen) ---
    wingbeat_samples: list[WingbeatSample] = []
    n_wb = max(2, int(window_duration_s / 6.0))
    for i in range(n_wb):
        t = i * (window_duration_s / (n_wb - 1))
        # Anomaly drives frequency past the high cap.
        base_freq = 7.0 + 18.0 * wingbeat_anomaly
        freq = base_freq + rng.uniform(-0.5, 0.5)
        reliable = rng.random() < 0.7
        wingbeat_samples.append(WingbeatSample(
            t_s=round(t, 3),
            frequency_hz=round(max(0.0, min(100.0, freq)), 3),
            reliable=reliable,
        ))

    # --- Thermal samples ---
    thermal_samples: list[BodyThermalSample] = []
    n_thermal = max(2, int(window_duration_s / 5.0))
    for i in range(n_thermal):
        t = i * (window_duration_s / (n_thermal - 1))
        elev = thermal_elevation + rng.uniform(-0.05, 0.05)
        thermal_samples.append(BodyThermalSample(
            t_s=round(t, 3),
            elevation=round(max(0.0, min(1.0, elev)), 3),
        ))

    # --- Dead-bird candidates ---
    candidates: list[DeadBirdCandidate] = []
    for i in range(dead_bird_count):
        t = (i + 0.5) * (window_duration_s / max(1, dead_bird_count))
        conf = 0.7 + rng.uniform(-0.1, 0.2)
        candidates.append(DeadBirdCandidate(
            t_s=round(t, 3),
            confidence=round(max(0.0, min(1.0, conf)), 3),
        ))

    return BirdObservation(
        obs_token=obs_token,
        station_id=station_id,
        location_handle=location_handle,
        window_duration_s=window_duration_s,
        expected_species=expected_species,
        call_samples=call_samples,
        wingbeat_samples=wingbeat_samples,
        thermal_samples=thermal_samples,
        dead_bird_candidates=candidates,
    )


def demo_observations() -> list[BirdObservation]:
    """Five demo observations across the channel space.

    1. Quiet station — calls present, no alerts.
    2. Distress vocalisations elevated → distress urgent.
    3. Wing-beat frequency high → vitals urgent.
    4. Mortality-cluster + thermal both fire → combined
       'candidate mortality cluster — sampling recommended'
       alert (the surveillance-overreach-safe wording).
    5. Expected calls absent + distress elevated.
    """
    return [
        generate_observation(
            obs_token="OBS-001", station_id="station-A",
            location_handle="grid-1", seed=1,
        ),
        generate_observation(
            obs_token="OBS-002", station_id="station-B",
            location_handle="grid-2",
            distress_fraction=0.50, seed=2,
        ),
        generate_observation(
            obs_token="OBS-003", station_id="station-C",
            location_handle="grid-3",
            wingbeat_anomaly=0.85, seed=3,
        ),
        generate_observation(
            obs_token="OBS-004", station_id="station-D",
            location_handle="zone-north",
            thermal_elevation=0.85, dead_bird_count=8, seed=4,
        ),
        generate_observation(
            obs_token="OBS-005", station_id="station-E",
            location_handle="grid-5",
            expected_species_present_fraction=0.0,
            distress_fraction=0.45, seed=5,
        ),
    ]

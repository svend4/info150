"""Deterministic synthetic pen-pass generator.

Real aquaculture footage is partner-protected. The library
is exercised against synthetic ``PenObservation`` records
with both vision-derived and water-chemistry-derived
samples.

Seeds use ``zlib.crc32`` for cross-run stability.
"""

from __future__ import annotations

import random

from biocore.seeds import crc32_seed

from ..core.enums import Species, WaterCondition
from ..core.models import (
    GillRateSample,
    MortalityFloorSample,
    PenObservation,
    SchoolCohesionSample,
    SeaLiceSample,
    WaterChemistrySample,
)


_DEFAULT_WINDOW_S = 600.0  # 10-minute pen pass


def _rng(seed_source: tuple[str, int]) -> random.Random:
    """Build a deterministic RNG from a seed-source tuple.

    Delegates to ``biocore.seeds.crc32_seed`` (extracted in
    biocore tier-1).
    """
    return random.Random(crc32_seed(*seed_source))


def generate_observation(
    pen_id: str = "P-001",
    species: Species = "salmon",
    location_handle: str = "pen-A1",
    window_duration_s: float = _DEFAULT_WINDOW_S,
    gill_anomaly: float = 0.0,
    school_disruption: float = 0.0,
    sea_lice_burden: float = 0.0,
    mortality_count: int = 0,
    do_drop: float = 0.0,
    temp_anomaly: float = 0.0,
    water_condition: WaterCondition = "clear",
    seed: int = 0,
) -> PenObservation:
    """Build one synthetic PenObservation."""
    for name, val in (
        ("gill_anomaly", gill_anomaly),
        ("school_disruption", school_disruption),
        ("sea_lice_burden", sea_lice_burden),
        ("do_drop", do_drop),
        ("temp_anomaly", temp_anomaly),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if mortality_count < 0 or mortality_count > 200:
        raise ValueError(
            f"mortality_count out of range, got {mortality_count}"
        )
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")

    rng = _rng((pen_id, seed))

    # --- Gill-rate samples (one every ~30s) ---
    gill_samples: list[GillRateSample] = []
    n_gill = max(2, int(window_duration_s / 30.0))
    base_rate = 80.0 + 60.0 * gill_anomaly  # salmon-ish baseline
    for i in range(n_gill):
        t = i * (window_duration_s / (n_gill - 1))
        rate = base_rate + rng.uniform(-3.0, 3.0)
        gill_samples.append(GillRateSample(
            t_s=round(t, 3),
            rate_bpm=round(max(5.0, min(200.0, rate)), 2),
        ))

    # --- School-cohesion samples (every ~60s) ---
    school_samples: list[SchoolCohesionSample] = []
    n_sch = max(2, int(window_duration_s / 60.0))
    base_cohesion = max(0.0, min(1.0, 0.85 - 0.65 * school_disruption))
    for i in range(n_sch):
        t = i * (window_duration_s / (n_sch - 1))
        coh = base_cohesion + rng.uniform(-0.05, 0.05)
        school_samples.append(SchoolCohesionSample(
            t_s=round(t, 3),
            cohesion=round(max(0.0, min(1.0, coh)), 3),
        ))

    # --- Sea-lice samples ---
    lice_samples: list[SeaLiceSample] = []
    n_lice = max(2, int(window_duration_s / 120.0))
    for i in range(n_lice):
        t = i * (window_duration_s / (n_lice - 1))
        proxy = sea_lice_burden + rng.uniform(-0.05, 0.05)
        conf = 0.7 + rng.uniform(-0.05, 0.15)
        lice_samples.append(SeaLiceSample(
            t_s=round(t, 3),
            count_proxy=round(max(0.0, min(1.0, proxy)), 3),
            classifier_confidence=round(max(0.0, min(1.0, conf)), 3),
        ))

    # --- Mortality samples ---
    mortality_samples: list[MortalityFloorSample] = []
    if mortality_count > 0:
        for i in range(min(mortality_count, 5)):
            t = (i + 0.5) * (window_duration_s / max(1, min(mortality_count, 5)))
            count_chunk = (
                mortality_count // 5 if i < 4
                else mortality_count - 4 * (mortality_count // 5)
            )
            conf = 0.8 + rng.uniform(-0.1, 0.15)
            mortality_samples.append(MortalityFloorSample(
                t_s=round(t, 3),
                count=count_chunk,
                confidence=round(max(0.0, min(1.0, conf)), 3),
            ))

    # --- Water-chemistry samples ---
    chem_samples: list[WaterChemistrySample] = []
    n_chem = max(2, int(window_duration_s / 120.0))
    base_do = max(1.0, 8.0 - 7.0 * do_drop)  # salmon needs >= 6
    base_temp = 12.0 + 10.0 * temp_anomaly
    base_turbidity = {
        "clear": 2.0,
        "turbid": 25.0,
        "silt_storm": 80.0,
    }[water_condition]
    for i in range(n_chem):
        t = i * (window_duration_s / (n_chem - 1))
        do = base_do + rng.uniform(-0.3, 0.3)
        temp = base_temp + rng.uniform(-0.5, 0.5)
        turb = base_turbidity + rng.uniform(-1.0, 1.0)
        chem_samples.append(WaterChemistrySample(
            t_s=round(t, 3),
            dissolved_oxygen_mg_l=round(max(0.0, min(25.0, do)), 2),
            temperature_c=round(max(-2.0, min(40.0, temp)), 2),
            salinity_ppt=round(32.0 + rng.uniform(-0.5, 0.5), 2),
            turbidity_ntu=round(max(0.0, min(200.0, turb)), 2),
        ))

    return PenObservation(
        pen_id=pen_id,
        species=species,
        location_handle=location_handle,
        window_duration_s=window_duration_s,
        water_condition=water_condition,
        gill_rate_samples=gill_samples,
        school_samples=school_samples,
        sea_lice_samples=lice_samples,
        mortality_samples=mortality_samples,
        water_chemistry_samples=chem_samples,
    )


def demo_observations() -> list[PenObservation]:
    """Five demo pen-passes covering the channel space.

    1. Steady salmon pen, clear water → no alerts.
    2. Sea-lice burden rising → urgent via lice channel.
    3. Mortality + low DO → CROSS-MODAL combined alert
       (the architectural feature for this sibling).
    4. School cohesion lost — single-channel urgent.
    5. Turbid water + minor gill anomaly → vision channels
       blend toward neutral; calibration alert may surface.
    """
    return [
        generate_observation(
            pen_id="P-001", species="salmon",
            location_handle="pen-A1", seed=1,
        ),
        generate_observation(
            pen_id="P-002", species="salmon",
            location_handle="pen-A2",
            sea_lice_burden=0.85, seed=2,
        ),
        # Cross-modal: mortality cluster + low DO together.
        generate_observation(
            pen_id="P-003", species="salmon",
            location_handle="pen-B1",
            mortality_count=120, do_drop=0.85, seed=3,
        ),
        # School cohesion lost.
        generate_observation(
            pen_id="P-004", species="salmon",
            location_handle="pen-B2",
            school_disruption=0.85, seed=4,
        ),
        # Turbid water + minor gill anomaly — vision blends
        # toward neutral; the channel signals soften.
        generate_observation(
            pen_id="P-005", species="salmon",
            location_handle="pen-C1",
            gill_anomaly=0.30,
            water_condition="silt_storm", seed=5,
        ),
    ]

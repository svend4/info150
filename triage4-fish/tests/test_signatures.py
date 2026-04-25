"""Tests for the five aquaculture signatures."""

from __future__ import annotations

import pytest

from triage4_fish.core.models import (
    GillRateSample,
    MortalityFloorSample,
    SchoolCohesionSample,
    SeaLiceSample,
    WaterChemistrySample,
)
from triage4_fish.signatures.gill_rate import compute_gill_rate_safety
from triage4_fish.signatures.mortality_floor import (
    compute_mortality_safety,
)
from triage4_fish.signatures.school_cohesion import (
    compute_school_cohesion_safety,
)
from triage4_fish.signatures.sea_lice_burden import (
    compute_sea_lice_safety,
)
from triage4_fish.signatures.water_chemistry import (
    compute_water_chemistry,
)


# ---------------------------------------------------------------------------
# gill_rate
# ---------------------------------------------------------------------------


def test_gill_rate_empty_returns_one():
    assert compute_gill_rate_safety([], "salmon") == 1.0


def test_gill_rate_in_band_is_one():
    samples = [GillRateSample(t_s=i, rate_bpm=80) for i in range(5)]
    assert compute_gill_rate_safety(samples, "salmon") == 1.0


def test_gill_rate_above_high_cap_is_zero():
    samples = [GillRateSample(t_s=i, rate_bpm=160) for i in range(5)]
    assert compute_gill_rate_safety(samples, "salmon") == 0.0


def test_gill_rate_per_species_differs():
    samples = [GillRateSample(t_s=i, rate_bpm=85) for i in range(5)]
    # Salmon's hi cap is 100 — 85 in-band → 1.0.
    assert compute_gill_rate_safety(samples, "salmon") == 1.0
    # Sea bass hi cap is 80 — 85 above → < 1.0.
    assert compute_gill_rate_safety(samples, "sea_bass") < 1.0


def test_gill_rate_rejects_unknown_species():
    with pytest.raises(KeyError):
        compute_gill_rate_safety(
            [GillRateSample(t_s=0, rate_bpm=80)],
            "koi",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# school_cohesion
# ---------------------------------------------------------------------------


def test_school_empty_returns_one():
    assert compute_school_cohesion_safety([]) == 1.0


def test_school_tight_returns_one():
    samples = [SchoolCohesionSample(t_s=i, cohesion=0.85) for i in range(5)]
    assert compute_school_cohesion_safety(samples) == 1.0


def test_school_scattered_returns_zero():
    samples = [SchoolCohesionSample(t_s=i, cohesion=0.10) for i in range(5)]
    assert compute_school_cohesion_safety(samples) == 0.0


def test_school_partial_band():
    samples = [SchoolCohesionSample(t_s=i, cohesion=0.40) for i in range(5)]
    score = compute_school_cohesion_safety(samples)
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# sea_lice_burden
# ---------------------------------------------------------------------------


def test_sea_lice_empty_returns_one():
    assert compute_sea_lice_safety([]) == 1.0


def test_sea_lice_no_burden_returns_one():
    samples = [
        SeaLiceSample(t_s=i, count_proxy=0.0, classifier_confidence=0.8)
        for i in range(3)
    ]
    assert compute_sea_lice_safety(samples) == 1.0


def test_sea_lice_high_burden_returns_low():
    samples = [
        SeaLiceSample(t_s=i, count_proxy=0.85, classifier_confidence=0.8)
        for i in range(3)
    ]
    score = compute_sea_lice_safety(samples)
    assert score < 0.20


def test_sea_lice_low_confidence_filtered():
    samples = [
        SeaLiceSample(t_s=i, count_proxy=0.85, classifier_confidence=0.2)
        for i in range(3)
    ]
    # All below confidence floor → returns 1.0.
    assert compute_sea_lice_safety(samples) == 1.0


# ---------------------------------------------------------------------------
# mortality_floor
# ---------------------------------------------------------------------------


def test_mortality_empty_returns_one():
    assert compute_mortality_safety([]) == 1.0


def test_mortality_low_confidence_filtered():
    samples = [
        MortalityFloorSample(t_s=i, count=20, confidence=0.2)
        for i in range(3)
    ]
    assert compute_mortality_safety(samples) == 1.0


def test_mortality_high_count_returns_zero():
    samples = [
        MortalityFloorSample(t_s=i, count=15, confidence=0.9)
        for i in range(3)
    ]
    # weighted_total = 15*0.9*3 = 40.5 >= 30 → 0.
    assert compute_mortality_safety(samples) == 0.0


def test_mortality_partial_count():
    samples = [
        MortalityFloorSample(t_s=i, count=4, confidence=0.7)
        for i in range(3)
    ]
    score = compute_mortality_safety(samples)
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# water_chemistry — multi-modal output
# ---------------------------------------------------------------------------


def test_water_empty_returns_neutral():
    reading = compute_water_chemistry([], "salmon")
    assert reading.safety == 1.0
    assert reading.vision_confidence == 1.0


def test_water_clean_returns_high():
    samples = [
        WaterChemistrySample(
            t_s=i, dissolved_oxygen_mg_l=8.0, temperature_c=10.0,
            salinity_ppt=32.0, turbidity_ntu=2.0,
        )
        for i in range(3)
    ]
    reading = compute_water_chemistry(samples, "salmon")
    assert reading.safety == 1.0
    assert reading.vision_confidence == 1.0


def test_water_low_do_drops_safety():
    samples = [
        WaterChemistrySample(
            t_s=i, dissolved_oxygen_mg_l=2.5, temperature_c=10.0,
            salinity_ppt=32.0, turbidity_ntu=2.0,
        )
        for i in range(3)
    ]
    reading = compute_water_chemistry(samples, "salmon")
    # DO 2.5 < urgent cap 3.0 → safety 0.
    assert reading.safety == 0.0


def test_water_high_temp_drops_safety():
    samples = [
        WaterChemistrySample(
            t_s=i, dissolved_oxygen_mg_l=8.0, temperature_c=20.0,
            salinity_ppt=32.0, turbidity_ntu=2.0,
        )
        for i in range(3)
    ]
    reading = compute_water_chemistry(samples, "salmon")
    # Salmon temp_high_ok=14, temp_urgent_high=18; 20 > 18 → 0.
    assert reading.safety == 0.0


def test_water_turbidity_lowers_vision_confidence():
    """Critical multi-modal property: turbidity drives the
    vision_confidence factor down without affecting the
    safety score in isolation."""
    clear = compute_water_chemistry([
        WaterChemistrySample(
            t_s=0, dissolved_oxygen_mg_l=8.0, temperature_c=10.0,
            salinity_ppt=32.0, turbidity_ntu=2.0,
        ),
    ], "salmon")
    silt = compute_water_chemistry([
        WaterChemistrySample(
            t_s=0, dissolved_oxygen_mg_l=8.0, temperature_c=10.0,
            salinity_ppt=32.0, turbidity_ntu=80.0,
        ),
    ], "salmon")
    # Both have good DO + temp → safety 1.0.
    assert clear.safety == 1.0
    assert silt.safety == 1.0
    # But silt-storm reduces vision_confidence.
    assert silt.vision_confidence < clear.vision_confidence
    assert silt.vision_confidence <= 0.4


def test_water_per_species_temp_band_differs():
    """Tilapia tolerates much warmer water than salmon."""
    samples = [
        WaterChemistrySample(
            t_s=0, dissolved_oxygen_mg_l=5.0, temperature_c=28.0,
            salinity_ppt=32.0, turbidity_ntu=2.0,
        ),
    ]
    salmon_reading = compute_water_chemistry(samples, "salmon")
    tilapia_reading = compute_water_chemistry(samples, "tilapia")
    # 28 °C: salmon urgent (>18); tilapia in band (22-30).
    assert salmon_reading.safety == 0.0
    assert tilapia_reading.safety == 1.0


def test_water_rejects_unknown_species():
    with pytest.raises(KeyError):
        compute_water_chemistry(
            [WaterChemistrySample(
                t_s=0, dissolved_oxygen_mg_l=8.0, temperature_c=10.0,
                salinity_ppt=32.0, turbidity_ntu=2.0,
            )],
            "koi",  # type: ignore[arg-type]
        )

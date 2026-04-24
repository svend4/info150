"""Tests for the four crowd-safety signatures."""

from __future__ import annotations

import pytest

from triage4_crowd.core.models import (
    DensityReading,
    FlowSample,
    MedicalCandidate,
    PressureReading,
)
from triage4_crowd.signatures.density_signature import compute_density_safety
from triage4_crowd.signatures.flow_signature import compute_flow_safety
from triage4_crowd.signatures.medical_in_crowd import compute_medical_safety
from triage4_crowd.signatures.pressure_wave import compute_pressure_safety


# ---------------------------------------------------------------------------
# density_signature
# ---------------------------------------------------------------------------


def test_density_empty_returns_one():
    assert compute_density_safety([], "standing") == 1.0


def test_density_comfort_band_is_one():
    readings = [
        DensityReading(t_s=i, persons_per_m2=1.0)
        for i in range(5)
    ]
    assert compute_density_safety(readings, "standing") == 1.0


def test_density_critical_band_is_zero():
    # standing critical = 6.0 p/m².
    readings = [
        DensityReading(t_s=i, persons_per_m2=7.0)
        for i in range(5)
    ]
    assert compute_density_safety(readings, "standing") == 0.0


def test_density_middle_band_partial():
    # standing: comfort=2.0, dense=4.0, critical=6.0.
    readings = [
        DensityReading(t_s=i, persons_per_m2=3.0)
        for i in range(5)
    ]
    score = compute_density_safety(readings, "standing")
    assert 0.5 < score < 1.0


def test_density_per_zone_kind_differs():
    # transit_platform: comfort=1.2, dense=2.5, critical=4.5.
    # standing:         comfort=2.0, dense=4.0, critical=6.0.
    # At 2.5 p/m²:
    #   transit_platform → in the dense band, ~0.5
    #   standing         → in comfort-to-dense band, higher
    readings = [DensityReading(t_s=0, persons_per_m2=2.5)]
    transit_score = compute_density_safety(readings, "transit_platform")
    standing_score = compute_density_safety(readings, "standing")
    assert standing_score > transit_score


def test_density_rejects_unknown_zone_kind():
    with pytest.raises(KeyError):
        compute_density_safety(
            [DensityReading(t_s=0, persons_per_m2=1.0)],
            "balcony",  # type: ignore[arg-type]
        )


def test_density_uses_median_not_max():
    # Four comfortable + one spike — median is in comfort
    # band, so score stays high despite the spike.
    readings = [
        DensityReading(t_s=i, persons_per_m2=1.0) for i in range(4)
    ]
    readings.append(DensityReading(t_s=5, persons_per_m2=7.0))
    score = compute_density_safety(readings, "standing")
    assert score == 1.0


# ---------------------------------------------------------------------------
# flow_signature
# ---------------------------------------------------------------------------


def test_flow_empty_returns_one():
    assert compute_flow_safety([]) == 1.0


def test_flow_static_is_safe():
    samples = [
        FlowSample(t_s=i, net_direction="static", magnitude=0.2, compaction=0.2)
        for i in range(5)
    ]
    assert compute_flow_safety(samples) == 1.0


def test_flow_crossflow_is_safe_regardless_of_magnitude():
    # Crossflow is a design problem but not a crush precursor.
    samples = [
        FlowSample(t_s=i, net_direction="crossflow", magnitude=0.9, compaction=0.9)
        for i in range(5)
    ]
    assert compute_flow_safety(samples) == 1.0


def test_flow_uni_directional_compaction_is_unsafe():
    samples = [
        FlowSample(t_s=i, net_direction="in", magnitude=0.9, compaction=0.9)
        for i in range(5)
    ]
    score = compute_flow_safety(samples)
    assert score < 0.2


def test_flow_worst_sample_dominates():
    # One bad flow sample among many good ones — worst-
    # sample domination because flow-compaction worsens
    # quickly.
    samples = [
        FlowSample(t_s=i, net_direction="static", magnitude=0.1, compaction=0.1)
        for i in range(5)
    ]
    samples.append(
        FlowSample(t_s=100, net_direction="in", magnitude=0.9, compaction=0.9)
    )
    assert compute_flow_safety(samples) < 0.2


# ---------------------------------------------------------------------------
# pressure_wave
# ---------------------------------------------------------------------------


def test_pressure_empty_returns_one():
    assert compute_pressure_safety([]) == 1.0


def test_pressure_quiet_is_safe():
    readings = [
        PressureReading(t_s=i, pressure_rms=0.05)
        for i in range(10)
    ]
    assert compute_pressure_safety(readings) == 1.0


def test_pressure_sustained_high_is_unsafe():
    readings = [
        PressureReading(t_s=i, pressure_rms=0.85)
        for i in range(10)
    ]
    assert compute_pressure_safety(readings) == 0.0


def test_pressure_one_spike_does_not_crash_score():
    # Single elevated sample among many low — score stays high.
    readings = [
        PressureReading(t_s=i, pressure_rms=0.05) for i in range(9)
    ]
    readings.append(PressureReading(t_s=10, pressure_rms=0.9))
    score = compute_pressure_safety(readings)
    assert 0.5 < score < 1.0


# ---------------------------------------------------------------------------
# medical_in_crowd
# ---------------------------------------------------------------------------


def test_medical_empty_returns_one():
    assert compute_medical_safety([]) == 1.0


def test_medical_single_high_confidence_is_low_score():
    candidates = [
        MedicalCandidate(candidate_id="c1", t_s=0, confidence=0.85),
    ]
    score = compute_medical_safety(candidates)
    assert score < 0.2


def test_medical_low_confidence_candidates_get_partial_credit():
    # Single low-confidence candidate — partial weight, not full.
    candidates = [
        MedicalCandidate(candidate_id="c1", t_s=0, confidence=0.50),
    ]
    score = compute_medical_safety(candidates)
    assert 0.5 < score < 1.0


def test_medical_below_low_threshold_does_not_count():
    candidates = [
        MedicalCandidate(candidate_id="c1", t_s=0, confidence=0.3),
    ]
    assert compute_medical_safety(candidates) == 1.0


def test_medical_multiple_candidates_accumulate():
    candidates = [
        MedicalCandidate(candidate_id=f"c{i}", t_s=i, confidence=0.60)
        for i in range(5)
    ]
    score = compute_medical_safety(candidates)
    # Several medium-confidence candidates accumulate to
    # drive the score low.
    assert score < 0.3

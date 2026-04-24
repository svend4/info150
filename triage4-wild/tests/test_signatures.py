"""Tests for the four wildlife-health signatures."""

from __future__ import annotations

from triage4_wild.core.models import (
    BodyConditionSample,
    GaitSample,
    QuadrupedPoseSample,
    ThermalSample,
)
from triage4_wild.signatures.body_condition import (
    compute_body_condition_safety,
)
from triage4_wild.signatures.postural_collapse import compute_postural_safety
from triage4_wild.signatures.quadruped_gait import compute_gait_safety
from triage4_wild.signatures.thermal_asymmetry import compute_thermal_safety


# ---------------------------------------------------------------------------
# quadruped_gait
# ---------------------------------------------------------------------------


def test_gait_empty_returns_one():
    assert compute_gait_safety([], []) == 1.0


def test_gait_symmetric_returns_one():
    pose = [
        QuadrupedPoseSample(t_s=i, limb_asymmetry=0.1, body_upright=0.9)
        for i in range(5)
    ]
    # cadence_steadiness=1.0 produces the full 1.0 multiplier;
    # lower steadiness values slightly discount even a
    # symmetric-gait score, which is by design.
    gait = [
        GaitSample(t_s=i, pace_mps=1.2, cadence_steadiness=1.0)
        for i in range(5)
    ]
    assert compute_gait_safety(pose, gait) == 1.0


def test_gait_severe_asymmetry_returns_low():
    pose = [
        QuadrupedPoseSample(t_s=i, limb_asymmetry=0.60, body_upright=0.9)
        for i in range(5)
    ]
    gait = [
        GaitSample(t_s=i, pace_mps=1.2, cadence_steadiness=0.5)
        for i in range(5)
    ]
    assert compute_gait_safety(pose, gait) < 0.5


def test_gait_cadence_multiplier_applied():
    """With moderate asymmetry, a non-rhythmic cadence
    should lower the score more than a steady cadence."""
    pose = [
        QuadrupedPoseSample(t_s=i, limb_asymmetry=0.35, body_upright=0.9)
        for i in range(5)
    ]
    steady = [
        GaitSample(t_s=i, pace_mps=1.2, cadence_steadiness=1.0)
        for i in range(5)
    ]
    unsteady = [
        GaitSample(t_s=i, pace_mps=1.2, cadence_steadiness=0.1)
        for i in range(5)
    ]
    steady_score = compute_gait_safety(pose, steady)
    unsteady_score = compute_gait_safety(pose, unsteady)
    assert unsteady_score < steady_score


def test_gait_uses_median_not_max():
    """One flinch frame with max asymmetry shouldn't tank
    an otherwise-healthy gait score."""
    pose = [
        QuadrupedPoseSample(t_s=i, limb_asymmetry=0.1, body_upright=0.9)
        for i in range(4)
    ]
    pose.append(
        QuadrupedPoseSample(t_s=5, limb_asymmetry=0.9, body_upright=0.9),
    )
    gait = [
        GaitSample(t_s=i, pace_mps=1.2, cadence_steadiness=0.95)
        for i in range(5)
    ]
    score = compute_gait_safety(pose, gait)
    # Median asymmetry = 0.1 → asym_score = 1.0.
    assert score >= 0.95


# ---------------------------------------------------------------------------
# thermal_asymmetry
# ---------------------------------------------------------------------------


def test_thermal_empty_returns_one():
    assert compute_thermal_safety([]) == 1.0


def test_thermal_no_hotspot_returns_one():
    samples = [ThermalSample(t_s=i, hotspot=0.05) for i in range(5)]
    assert compute_thermal_safety(samples) == 1.0


def test_thermal_severe_hotspot_returns_low():
    samples = [ThermalSample(t_s=0, hotspot=0.60)]
    assert compute_thermal_safety(samples) < 0.3


def test_thermal_worst_sample_dominates():
    """One high-confidence hotspot sample among quiet ones
    — a wound shows up in one IR pass and the library must
    flag it."""
    samples = [ThermalSample(t_s=i, hotspot=0.05) for i in range(5)]
    samples.append(ThermalSample(t_s=6, hotspot=0.55))
    score = compute_thermal_safety(samples)
    assert score < 0.5


def test_thermal_middle_band_partial():
    samples = [ThermalSample(t_s=i, hotspot=0.30) for i in range(5)]
    score = compute_thermal_safety(samples)
    assert 0.2 < score < 0.9


# ---------------------------------------------------------------------------
# postural_collapse
# ---------------------------------------------------------------------------


def test_postural_empty_returns_one():
    assert compute_postural_safety([]) == 1.0


def test_postural_all_upright_returns_one():
    samples = [
        QuadrupedPoseSample(t_s=i, limb_asymmetry=0.1, body_upright=0.9)
        for i in range(10)
    ]
    assert compute_postural_safety(samples) == 1.0


def test_postural_brief_low_frames_ordinary_rest():
    """≤ 25 % low-upright frames = grazing / brief rest. Score
    should stay high."""
    # 2 low + 8 upright = 0.2 fraction.
    samples = [
        QuadrupedPoseSample(t_s=i, limb_asymmetry=0.1, body_upright=0.2)
        for i in range(2)
    ]
    samples.extend([
        QuadrupedPoseSample(t_s=i + 2, limb_asymmetry=0.1, body_upright=0.9)
        for i in range(8)
    ])
    score = compute_postural_safety(samples)
    assert score >= 0.8


def test_postural_sustained_down_returns_low():
    """> 75 % low-upright fraction = sustained down pattern."""
    samples = [
        QuadrupedPoseSample(t_s=i, limb_asymmetry=0.1, body_upright=0.15)
        for i in range(8)
    ]
    samples.extend([
        QuadrupedPoseSample(t_s=i + 8, limb_asymmetry=0.1, body_upright=0.8)
        for i in range(2)
    ])
    score = compute_postural_safety(samples)
    assert score < 0.3


def test_postural_mid_band_partial():
    samples = [
        QuadrupedPoseSample(t_s=i, limb_asymmetry=0.1, body_upright=0.2)
        for i in range(5)
    ]
    samples.extend([
        QuadrupedPoseSample(t_s=i + 5, limb_asymmetry=0.1, body_upright=0.9)
        for i in range(5)
    ])
    score = compute_postural_safety(samples)
    assert 0.2 < score < 0.8


# ---------------------------------------------------------------------------
# body_condition
# ---------------------------------------------------------------------------


def test_body_condition_empty_returns_one():
    assert compute_body_condition_safety([]) == 1.0


def test_body_condition_healthy_returns_high():
    samples = [
        BodyConditionSample(t_s=i, condition_score=0.9)
        for i in range(5)
    ]
    assert compute_body_condition_safety(samples) == 0.9


def test_body_condition_emaciated_returns_low():
    samples = [
        BodyConditionSample(t_s=i, condition_score=0.2)
        for i in range(5)
    ]
    assert compute_body_condition_safety(samples) == 0.2

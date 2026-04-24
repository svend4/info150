"""Tests for the four site-safety signatures."""

from __future__ import annotations

from triage4_site.core.models import (
    FatigueGaitSample,
    LiftingSample,
    PPESample,
    ThermalSample,
)
from triage4_site.signatures.fatigue_gait import compute_fatigue_safety
from triage4_site.signatures.heat_stress import compute_heat_safety
from triage4_site.signatures.lifting_posture import compute_lifting_safety
from triage4_site.signatures.ppe_compliance import compute_ppe_compliance


# ---------------------------------------------------------------------------
# ppe_compliance
# ---------------------------------------------------------------------------


def test_ppe_no_required_returns_one():
    samples = [PPESample(t_s=0, items_detected=())]
    assert compute_ppe_compliance(samples, required_ppe=()) == 1.0


def test_ppe_empty_samples_returns_zero_when_required():
    assert compute_ppe_compliance([], required_ppe=("hard_hat",)) == 0.0


def test_ppe_full_compliance():
    required = ("hard_hat", "vest", "harness")
    samples = [
        PPESample(t_s=i, items_detected=("hard_hat", "vest", "harness"))
        for i in range(5)
    ]
    assert compute_ppe_compliance(samples, required_ppe=required) == 1.0


def test_ppe_half_compliance():
    required = ("hard_hat",)
    samples = [
        PPESample(t_s=0, items_detected=("hard_hat",)),
        PPESample(t_s=1, items_detected=()),
    ]
    assert compute_ppe_compliance(samples, required_ppe=required) == 0.5


def test_ppe_extra_items_do_not_hurt_compliance():
    required = ("hard_hat",)
    samples = [
        PPESample(t_s=0, items_detected=("hard_hat", "glasses", "vest")),
    ]
    assert compute_ppe_compliance(samples, required_ppe=required) == 1.0


# ---------------------------------------------------------------------------
# lifting_posture
# ---------------------------------------------------------------------------


def test_lifting_empty_returns_one():
    assert compute_lifting_safety([]) == 1.0


def test_lifting_safe_angle_at_load():
    samples = [
        LiftingSample(t_s=i, back_angle_deg=25.0, load_kg=20.0)
        for i in range(3)
    ]
    assert compute_lifting_safety(samples) == 1.0


def test_lifting_unsafe_angle_at_load():
    samples = [
        LiftingSample(t_s=i, back_angle_deg=70.0, load_kg=20.0)
        for i in range(3)
    ]
    assert compute_lifting_safety(samples) == 0.0


def test_lifting_unloaded_deep_flexion_is_ignored():
    # Bending over at zero load is not an unsafe lift; its
    # load weight is 0 → contributes nothing to the score.
    samples = [
        LiftingSample(t_s=0, back_angle_deg=75.0, load_kg=0.0),
    ]
    assert compute_lifting_safety(samples) == 1.0


def test_lifting_partial_middle_band():
    samples = [
        LiftingSample(t_s=0, back_angle_deg=45.0, load_kg=20.0),
    ]
    score = compute_lifting_safety(samples)
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# heat_stress
# ---------------------------------------------------------------------------


def test_heat_empty_returns_one():
    assert compute_heat_safety([]) == 1.0


def test_heat_cool_day_safe():
    samples = [
        ThermalSample(t_s=i, skin_temp_c=33.5, ambient_temp_c=22.0)
        for i in range(3)
    ]
    assert compute_heat_safety(samples) == 1.0


def test_heat_marked_stress_low_score():
    # Elevated skin + hot ambient + no differential.
    samples = [
        ThermalSample(t_s=0, skin_temp_c=39.0, ambient_temp_c=38.5),
    ]
    assert compute_heat_safety(samples) < 0.2


def test_heat_ambient_alone_above_cap_still_safe_if_skin_cool():
    # Hot day but the worker has great cooling — differential
    # still wide, skin under the elevated band.
    samples = [
        ThermalSample(t_s=0, skin_temp_c=34.0, ambient_temp_c=22.0),
    ]
    score = compute_heat_safety(samples)
    assert score == 1.0


def test_heat_worst_sample_dominates():
    # One bad sample among many good — worst-sample
    # domination matches the physics (cooling compromised).
    samples = [
        ThermalSample(t_s=i, skin_temp_c=34.0, ambient_temp_c=22.0)
        for i in range(5)
    ]
    samples.append(
        ThermalSample(t_s=100, skin_temp_c=39.0, ambient_temp_c=38.5)
    )
    assert compute_heat_safety(samples) < 0.2


# ---------------------------------------------------------------------------
# fatigue_gait
# ---------------------------------------------------------------------------


def test_fatigue_few_samples_neutral():
    samples = [
        FatigueGaitSample(t_s=i, pace_mps=1.0, asymmetry=0.05)
        for i in range(3)
    ]
    # Below the minimum-window sample count — defaults to 1.0
    # (neutral), calibration alert separately surfaces the gap.
    assert compute_fatigue_safety(samples) == 1.0


def test_fatigue_fresh_shift_score_high():
    samples = [
        FatigueGaitSample(t_s=i * 10, pace_mps=1.25, asymmetry=0.02)
        for i in range(10)
    ]
    score = compute_fatigue_safety(samples)
    assert score >= 0.9


def test_fatigue_late_shift_pace_drop_lowers_score():
    early = [
        FatigueGaitSample(t_s=i * 10, pace_mps=1.25, asymmetry=0.05)
        for i in range(5)
    ]
    late = [
        FatigueGaitSample(t_s=100 + i * 10, pace_mps=0.8, asymmetry=0.05)
        for i in range(5)
    ]
    score = compute_fatigue_safety(early + late)
    # ~36 % pace drop → pace channel in the severe band.
    assert score < 0.5


def test_fatigue_rising_asymmetry_lowers_score():
    early = [
        FatigueGaitSample(t_s=i * 10, pace_mps=1.25, asymmetry=0.05)
        for i in range(5)
    ]
    late = [
        FatigueGaitSample(t_s=100 + i * 10, pace_mps=1.25, asymmetry=0.30)
        for i in range(5)
    ]
    score = compute_fatigue_safety(early + late)
    # Asymmetry above severe band, pace unchanged — score still
    # drops meaningfully (avg of the two channels).
    assert 0.3 <= score < 0.6

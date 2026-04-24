"""Tests for the four pet-health signatures."""

from __future__ import annotations

import pytest

from triage4_pet.core.models import (
    BreathingSample,
    GaitSample,
    PainBehaviorSample,
    VitalHRSample,
)
from triage4_pet.signatures.cardiac_band import compute_cardiac_safety
from triage4_pet.signatures.gait_asymmetry import compute_gait_safety
from triage4_pet.signatures.pain_behaviors import compute_pain_safety
from triage4_pet.signatures.respiratory_distress import (
    compute_respiratory_safety,
)


# ---------------------------------------------------------------------------
# gait_asymmetry
# ---------------------------------------------------------------------------


def test_gait_empty_returns_one():
    assert compute_gait_safety([]) == 1.0


def test_gait_symmetric_gait_is_one():
    samples = [
        GaitSample(t_s=i, limb_asymmetry=0.10, pace_consistency=0.95)
        for i in range(5)
    ]
    assert compute_gait_safety(samples) == 1.0


def test_gait_severe_asymmetry_is_low():
    samples = [
        GaitSample(t_s=i, limb_asymmetry=0.55, pace_consistency=0.5)
        for i in range(5)
    ]
    assert compute_gait_safety(samples) < 0.2


def test_gait_moderate_asymmetry_partial():
    samples = [
        GaitSample(t_s=i, limb_asymmetry=0.35, pace_consistency=0.8)
        for i in range(5)
    ]
    score = compute_gait_safety(samples)
    assert 0.1 < score < 1.0


def test_gait_uses_median_not_max():
    samples = [
        GaitSample(t_s=i, limb_asymmetry=0.10, pace_consistency=0.9)
        for i in range(4)
    ]
    samples.append(
        GaitSample(t_s=5, limb_asymmetry=0.90, pace_consistency=0.9),
    )
    # Median is at i=2 → 0.10, so gait_score_pre_multiplier = 1.0
    # consistency ≈ 0.9 → multiplier ≈ 0.96.
    score = compute_gait_safety(samples)
    assert score >= 0.9


# ---------------------------------------------------------------------------
# respiratory_distress
# ---------------------------------------------------------------------------


def test_respiratory_empty_returns_one():
    assert compute_respiratory_safety([], "dog") == 1.0


def test_respiratory_in_resting_band_is_one():
    samples = [
        BreathingSample(t_s=i, rate_bpm=18.0, at_rest=True)
        for i in range(5)
    ]
    assert compute_respiratory_safety(samples, "dog") == 1.0


def test_respiratory_above_cap_is_zero():
    # dog cap 60.
    samples = [
        BreathingSample(t_s=i, rate_bpm=65.0, at_rest=False)
        for i in range(5)
    ]
    assert compute_respiratory_safety(samples, "dog") == 0.0


def test_respiratory_panting_at_rest_adjustment_fires():
    # 35 bpm is above dog's 30 bpm resting cap. If at_rest=True,
    # the panting-at-rest adjustment kicks in and drops the
    # score further.
    samples_rest = [
        BreathingSample(t_s=i, rate_bpm=35.0, at_rest=True)
        for i in range(5)
    ]
    samples_active = [
        BreathingSample(t_s=i, rate_bpm=35.0, at_rest=False)
        for i in range(5)
    ]
    rest_score = compute_respiratory_safety(samples_rest, "dog")
    active_score = compute_respiratory_safety(samples_active, "dog")
    assert rest_score < active_score


def test_respiratory_per_species_differs():
    # 25 bpm is inside dog's (10-30) resting band but at the
    # edge of cat's (20-30) band.
    samples = [
        BreathingSample(t_s=i, rate_bpm=25.0, at_rest=True)
        for i in range(5)
    ]
    assert compute_respiratory_safety(samples, "dog") == 1.0
    assert compute_respiratory_safety(samples, "cat") == 1.0
    # 8 bpm is at the very low end of dog's band, way below
    # cat's (20-30) band.
    samples_low = [
        BreathingSample(t_s=i, rate_bpm=8.0, at_rest=True)
        for i in range(5)
    ]
    dog_low = compute_respiratory_safety(samples_low, "dog")
    cat_low = compute_respiratory_safety(samples_low, "cat")
    assert cat_low < dog_low  # lower rate is even more abnormal for cats


def test_respiratory_rejects_unknown_species():
    with pytest.raises(KeyError):
        compute_respiratory_safety(
            [BreathingSample(t_s=0, rate_bpm=20.0, at_rest=True)],
            "iguana",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# cardiac_band
# ---------------------------------------------------------------------------


def test_cardiac_empty_returns_one():
    assert compute_cardiac_safety([], "dog") == 1.0


def test_cardiac_unreliable_only_returns_one():
    """If no HR samples are reliable, score is neutral 1.0 —
    calibration layer surfaces the reliability gap."""
    samples = [
        VitalHRSample(t_s=i, hr_bpm=200.0, reliable=False)
        for i in range(5)
    ]
    assert compute_cardiac_safety(samples, "dog") == 1.0


def test_cardiac_in_band_is_one():
    samples = [
        VitalHRSample(t_s=i, hr_bpm=100.0, reliable=True)
        for i in range(5)
    ]
    assert compute_cardiac_safety(samples, "dog") == 1.0


def test_cardiac_above_high_cap_is_zero():
    # dog high cap = 200.
    samples = [
        VitalHRSample(t_s=i, hr_bpm=210.0, reliable=True)
        for i in range(5)
    ]
    assert compute_cardiac_safety(samples, "dog") == 0.0


def test_cardiac_below_low_cap_is_zero():
    # dog low cap = 40.
    samples = [
        VitalHRSample(t_s=i, hr_bpm=35.0, reliable=True)
        for i in range(5)
    ]
    assert compute_cardiac_safety(samples, "dog") == 0.0


def test_cardiac_per_species_differs():
    # 180 bpm is inside cat's (140-220) band but well above
    # dog's (60-140) band.
    samples = [
        VitalHRSample(t_s=i, hr_bpm=180.0, reliable=True)
        for i in range(5)
    ]
    assert compute_cardiac_safety(samples, "cat") == 1.0
    assert compute_cardiac_safety(samples, "dog") < 1.0


def test_cardiac_rejects_unknown_species():
    with pytest.raises(KeyError):
        compute_cardiac_safety(
            [VitalHRSample(t_s=0, hr_bpm=100.0, reliable=True)],
            "iguana",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# pain_behaviors
# ---------------------------------------------------------------------------


def test_pain_empty_returns_one():
    assert compute_pain_safety([], "dog") == 1.0


def test_pain_dog_panting_at_rest_drops_score():
    samples = [
        PainBehaviorSample(
            t_s=0, kind="panting_at_rest", confidence=1.0,
        ),
    ]
    # dog: panting_at_rest weight = 0.30 → score = 0.70.
    score = compute_pain_safety(samples, "dog")
    assert 0.65 < score < 0.75


def test_pain_cat_hiding_is_stronger_than_dog_hiding():
    samples = [
        PainBehaviorSample(t_s=0, kind="hiding", confidence=1.0),
    ]
    # cat hiding weight = 0.30, dog hiding weight = 0.15.
    cat_score = compute_pain_safety(samples, "cat")
    dog_score = compute_pain_safety(samples, "dog")
    assert cat_score < dog_score


def test_pain_multiple_behaviors_stack():
    samples = [
        PainBehaviorSample(t_s=0, kind="hiding", confidence=1.0),
        PainBehaviorSample(t_s=1, kind="ear_position", confidence=1.0),
        PainBehaviorSample(t_s=2, kind="hunched_posture", confidence=1.0),
    ]
    # cat: hiding 0.30 + ear_position 0.25 + hunched 0.20 = 0.75
    # → score = 0.25.
    score = compute_pain_safety(samples, "cat")
    assert 0.20 < score < 0.30


def test_pain_duplicate_kinds_dont_stack():
    samples = [
        PainBehaviorSample(t_s=0, kind="hiding", confidence=1.0),
        PainBehaviorSample(t_s=5, kind="hiding", confidence=1.0),
    ]
    # cat hiding = 0.30 (once) → score = 0.70.
    score = compute_pain_safety(samples, "cat")
    assert 0.65 < score < 0.75


def test_pain_confidence_scales_weight():
    samples_high = [
        PainBehaviorSample(t_s=0, kind="hiding", confidence=1.0),
    ]
    samples_low = [
        PainBehaviorSample(t_s=0, kind="hiding", confidence=0.5),
    ]
    high_score = compute_pain_safety(samples_high, "cat")
    low_score = compute_pain_safety(samples_low, "cat")
    # Higher confidence → more weight → lower safety score.
    assert high_score < low_score

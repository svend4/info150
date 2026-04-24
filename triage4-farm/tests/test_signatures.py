"""Tests for lameness / respiratory / thermal signatures."""

from __future__ import annotations

import pytest

from triage4_farm.core.models import AnimalObservation, JointPoseSample
from triage4_farm.signatures.lameness_gait import compute_lameness_score
from triage4_farm.signatures.respiratory_rate import compute_respiratory_score
from triage4_farm.signatures.thermal_inflammation import compute_thermal_score


def _frame(pairs: list[tuple[str, float, float]]) -> list[JointPoseSample]:
    return [JointPoseSample(joint=n, x=x, y=y) for n, x, y in pairs]


# ---------------------------------------------------------------------------
# compute_lameness_score
# ---------------------------------------------------------------------------


def test_lameness_sound_gait_scores_one():
    frames: list[list[JointPoseSample]] = []
    for _ in range(6):
        frames.append(
            _frame([
                ("wither",    0.30, 0.30),
                ("rump",      0.70, 0.30),
                ("hock_l",    0.68, 0.70),
                ("hock_r",    0.72, 0.70),
                ("hoof_l",    0.68, 0.90),
                ("hoof_r",    0.72, 0.90),
            ])
        )
    obs = AnimalObservation(
        animal_id="A1",
        species="dairy_cow",
        pose_frames=frames,
        duration_s=2.0,
    )
    assert compute_lameness_score(obs) == 1.0


def test_lameness_mild_asymmetry_drops_score():
    frames: list[list[JointPoseSample]] = []
    for _ in range(6):
        frames.append(
            _frame([
                ("wither",    0.30, 0.30),
                ("rump",      0.70, 0.30),
                ("hock_l",    0.68, 0.72),   # offset
                ("hock_r",    0.72, 0.70),
                ("hoof_l",    0.68, 0.92),
                ("hoof_r",    0.72, 0.90),
            ])
        )
    obs = AnimalObservation(
        animal_id="A1",
        species="dairy_cow",
        pose_frames=frames,
        duration_s=2.0,
    )
    score = compute_lameness_score(obs)
    assert 0.5 < score < 1.0


def test_lameness_severe_asymmetry_scores_low():
    frames: list[list[JointPoseSample]] = []
    for _ in range(6):
        frames.append(
            _frame([
                ("wither",    0.30, 0.30),
                ("rump",      0.70, 0.30),
                ("hock_l",    0.68, 0.50),   # big offset
                ("hock_r",    0.72, 0.80),
                ("hoof_l",    0.68, 0.60),
                ("hoof_r",    0.72, 0.92),
            ])
        )
    obs = AnimalObservation(
        animal_id="A1",
        species="dairy_cow",
        pose_frames=frames,
        duration_s=2.0,
    )
    assert compute_lameness_score(obs) < 0.5


def test_lameness_empty_obs_returns_one():
    obs = AnimalObservation(animal_id="A1", species="dairy_cow")
    assert compute_lameness_score(obs) == 1.0


def test_lameness_no_paired_joints_returns_one():
    frames = [_frame([("wither", 0.30, 0.30), ("rump", 0.70, 0.30)])]
    obs = AnimalObservation(
        animal_id="A1",
        species="dairy_cow",
        pose_frames=frames,
        duration_s=2.0,
    )
    assert compute_lameness_score(obs) == 1.0


def test_lameness_custom_pairs_respected():
    frame = _frame([
        ("wither",    0.30, 0.30),
        ("rump",      0.70, 0.30),
        ("hock_l",    0.68, 0.70),
        ("hock_r",    0.72, 0.70),
        # Injected side-specific joints — default pair list
        # does not include "carpus_*" so asymmetry here is
        # invisible to the default scorer.
        ("carpus_l",  0.65, 0.55),
        ("carpus_r",  0.75, 0.80),
    ])
    obs = AnimalObservation(
        animal_id="A1",
        species="dairy_cow",
        pose_frames=[frame],
        duration_s=2.0,
    )
    default_score = compute_lameness_score(obs)
    custom_score = compute_lameness_score(
        obs,
        pairs=(("carpus_l", "carpus_r"),),
    )
    assert default_score == 1.0
    assert custom_score < 1.0


# ---------------------------------------------------------------------------
# compute_respiratory_score
# ---------------------------------------------------------------------------


def test_respiratory_none_when_missing():
    assert compute_respiratory_score(None, "dairy_cow") is None


def test_respiratory_one_inside_resting_band():
    assert compute_respiratory_score(30, "dairy_cow") == 1.0
    assert compute_respiratory_score(35, "pig") == 1.0
    assert compute_respiratory_score(30, "chicken") == 1.0


def test_respiratory_zero_at_or_above_cap():
    # cow cap 60, pig cap 70, chicken cap 80
    assert compute_respiratory_score(60, "dairy_cow") == pytest.approx(0.0)
    assert compute_respiratory_score(70, "pig") == pytest.approx(0.0)
    assert compute_respiratory_score(80, "chicken") == pytest.approx(0.0)
    assert compute_respiratory_score(90, "dairy_cow") == 0.0


def test_respiratory_half_in_elevated_range():
    # cow: hi=40, cap=60. midpoint=50 → 0.5.
    score = compute_respiratory_score(50, "dairy_cow")
    assert score is not None
    assert score == pytest.approx(0.5, abs=1e-6)


def test_respiratory_below_resting_band_scores_lower():
    # cow resting_low = 20. Value 8 < 10 (= lo/2) → 0.
    assert compute_respiratory_score(8, "dairy_cow") == 0.0
    # Value 15 is between lo/2=10 and lo=20 → partial score.
    score = compute_respiratory_score(15, "dairy_cow")
    assert score is not None
    assert 0.0 < score < 1.0


def test_respiratory_rejects_unknown_species():
    with pytest.raises(KeyError):
        compute_respiratory_score(30, "alpaca")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# compute_thermal_score
# ---------------------------------------------------------------------------


def test_thermal_none_when_missing():
    assert compute_thermal_score(None) is None


def test_thermal_one_below_normal_cap():
    assert compute_thermal_score(0.05) == 1.0
    assert compute_thermal_score(0.15) == 1.0


def test_thermal_decays_in_concern_range():
    score = compute_thermal_score(0.30)
    assert score is not None
    assert 0.3 < score < 1.0


def test_thermal_drops_past_concern_cap():
    score = compute_thermal_score(0.50)
    assert score is not None
    assert score < 0.3


def test_thermal_rejects_out_of_range():
    with pytest.raises(ValueError):
        compute_thermal_score(1.5)
    with pytest.raises(ValueError):
        compute_thermal_score(-0.1)

"""Tests for pose_symmetry + breathing_recovery signatures."""

from __future__ import annotations

import pytest

from triage4_fit.core.models import JointPoseSample, RepObservation
from triage4_fit.signatures.breathing_recovery import estimate_recovery_quality
from triage4_fit.signatures.pose_symmetry import compute_rep_symmetry


def _frame(pairs: list[tuple[str, float, float]]) -> list[JointPoseSample]:
    return [JointPoseSample(joint=n, x=x, y=y) for n, x, y in pairs]


# ---------------------------------------------------------------------------
# compute_rep_symmetry
# ---------------------------------------------------------------------------


def test_symmetric_rep_scores_near_one():
    # Shoulders + hips at identical heights L/R, no asymmetry.
    frames: list[list[JointPoseSample]] = []
    for _ in range(6):
        frames.append(
            _frame([
                ("shoulder_l", 0.45, 0.30),
                ("shoulder_r", 0.55, 0.30),
                ("hip_l",      0.47, 0.60),
                ("hip_r",      0.53, 0.60),
            ])
        )
    rep = RepObservation(rep_index=0, duration_s=2.5, samples=frames)
    score = compute_rep_symmetry(rep)
    assert score == 1.0


def test_asymmetric_rep_drops_score():
    # Left hip sits 10 % body-scale higher than right throughout.
    frames: list[list[JointPoseSample]] = []
    for _ in range(6):
        frames.append(
            _frame([
                ("shoulder_l", 0.45, 0.30),
                ("shoulder_r", 0.55, 0.30),
                ("hip_l",      0.47, 0.55),   # higher than right
                ("hip_r",      0.53, 0.60),
            ])
        )
    rep = RepObservation(rep_index=0, duration_s=2.5, samples=frames)
    score = compute_rep_symmetry(rep)
    assert 0.3 < score < 0.95


def test_severely_asymmetric_rep_scores_low():
    frames: list[list[JointPoseSample]] = []
    for _ in range(6):
        frames.append(
            _frame([
                ("shoulder_l", 0.45, 0.30),
                ("shoulder_r", 0.55, 0.30),
                ("hip_l",      0.47, 0.40),   # very different
                ("hip_r",      0.53, 0.70),
            ])
        )
    rep = RepObservation(rep_index=0, duration_s=2.5, samples=frames)
    score = compute_rep_symmetry(rep)
    assert score < 0.5


def test_empty_rep_returns_one():
    # No samples — can't judge asymmetry, assume OK.
    rep = RepObservation(rep_index=0, duration_s=2.5)
    assert compute_rep_symmetry(rep) == 1.0


def test_rep_without_paired_joints_returns_one():
    frame = _frame([("elbow_l", 0.4, 0.5)])   # no right-side pair
    rep = RepObservation(rep_index=0, duration_s=2.5, samples=[frame])
    assert compute_rep_symmetry(rep) == 1.0


def test_custom_pairs_respected():
    frame = _frame([
        ("shoulder_l", 0.45, 0.30),
        ("shoulder_r", 0.55, 0.30),
        ("hip_l",      0.47, 0.60),
        ("hip_r",      0.53, 0.60),
        # Injected unpaired foot-tip joints — shouldn't affect
        # default scoring because they're not in DEFAULT_PAIRS.
        ("toe_l",      0.47, 0.95),
        ("toe_r",      0.53, 0.80),   # big asymmetry here
    ])
    rep = RepObservation(rep_index=0, duration_s=2.5, samples=[frame])
    default_score = compute_rep_symmetry(rep)
    custom_score = compute_rep_symmetry(rep, pairs=(("toe_l", "toe_r"),))
    assert default_score == 1.0
    assert custom_score < 1.0


# ---------------------------------------------------------------------------
# estimate_recovery_quality
# ---------------------------------------------------------------------------


def test_recovery_none_when_no_vitals_provided():
    assert estimate_recovery_quality(None, None) is None


def test_recovery_one_when_vitals_at_rest():
    q = estimate_recovery_quality(post_set_hr=65, post_set_breathing=14)
    assert q == 1.0


def test_recovery_zero_when_vitals_extreme():
    q = estimate_recovery_quality(post_set_hr=130, post_set_breathing=40)
    assert q == pytest.approx(0.0, abs=1e-6)


def test_recovery_half_when_vitals_mid():
    q = estimate_recovery_quality(post_set_hr=92, post_set_breathing=24)
    assert q is not None
    assert 0.3 < q < 0.7


def test_recovery_averages_two_channels():
    # HR at rest (score 1.0), breathing at cap (score 0.0).
    # Average = 0.5.
    q = estimate_recovery_quality(post_set_hr=60, post_set_breathing=30)
    assert q == pytest.approx(0.5, abs=1e-6)


def test_recovery_single_channel_usable():
    # Only HR given — score should reflect HR alone.
    q = estimate_recovery_quality(post_set_hr=65, post_set_breathing=None)
    assert q == 1.0

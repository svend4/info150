import numpy as np
import pytest

from triage4.matching import (
    OrientConfig,
    OrientMatchResult,
    OrientProfile,
    batch_orient_match,
    best_orient_angle,
    compute_orient_profile,
    match_orient_pair,
    orient_similarity,
)


def _stripe_image(direction: str = "h", size: int = 32) -> np.ndarray:
    img = np.zeros((size, size), dtype=float)
    if direction == "h":
        img[size // 2, :] = 1.0
    else:
        img[:, size // 2] = 1.0
    return img


def test_orient_config_validation():
    with pytest.raises(ValueError):
        OrientConfig(n_bins=1)
    with pytest.raises(ValueError):
        OrientConfig(angle_step=0.0)
    with pytest.raises(ValueError):
        OrientConfig(max_angle=-1.0)


def test_orient_profile_rejects_bad_dominant():
    with pytest.raises(ValueError):
        OrientProfile(fragment_id=0, histogram=np.ones(36), dominant=400.0)


def test_compute_orient_profile_shape_and_dominant():
    profile = compute_orient_profile(_stripe_image("h"), fragment_id=1)
    assert isinstance(profile, OrientProfile)
    assert profile.n_bins == 36
    assert abs(profile.histogram.sum() - 1.0) < 1e-6  # normalised


def test_orient_similarity_identical_profiles_is_one():
    profile = compute_orient_profile(_stripe_image("h"))
    assert orient_similarity(profile, profile, angle_deg=0.0) == pytest.approx(1.0)


def test_best_orient_angle_on_identical_returns_zero():
    profile = compute_orient_profile(_stripe_image("h"))
    angle, score = best_orient_angle(profile, profile)
    assert angle == pytest.approx(0.0)
    assert score == pytest.approx(1.0)


def test_match_orient_pair_returns_result():
    a = compute_orient_profile(_stripe_image("h"), fragment_id=0)
    b = compute_orient_profile(_stripe_image("v"), fragment_id=1)
    result = match_orient_pair(a, b)
    assert isinstance(result, OrientMatchResult)
    assert result.pair == (0, 1)
    assert 0.0 <= result.best_score <= 1.0


def test_match_orient_pair_with_flip_tries_mirror():
    a = compute_orient_profile(_stripe_image("h"), fragment_id=0)
    b = compute_orient_profile(_stripe_image("v"), fragment_id=1)
    cfg = OrientConfig(use_flip=True)
    result = match_orient_pair(a, b, cfg)
    assert result.n_angles_tested > 1


def test_batch_orient_match_pairs_every_combination():
    profiles = [
        compute_orient_profile(_stripe_image("h"), fragment_id=0),
        compute_orient_profile(_stripe_image("v"), fragment_id=1),
        compute_orient_profile(_stripe_image("h"), fragment_id=2),
    ]
    results = batch_orient_match(profiles)
    # 3 profiles → 3 pairs (0,1), (0,2), (1,2).
    assert len(results) == 3


def test_profile_is_uniform_for_flat_image():
    flat = np.ones((16, 16), dtype=float)
    profile = compute_orient_profile(flat)
    assert profile.is_uniform is True

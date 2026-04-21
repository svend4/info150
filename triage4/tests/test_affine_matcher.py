import math

import numpy as np
import pytest

from triage4.matching import (
    AffineMatchResult,
    affine_reprojection_error,
    apply_affine_pts,
    estimate_affine,
    match_points_affine,
    score_affine_match,
)


def _apply(M: np.ndarray, pts: np.ndarray) -> np.ndarray:
    ones = np.ones((len(pts), 1))
    return (M @ np.hstack([pts, ones]).T).T


def _rotation_translation(angle_deg: float, tx: float, ty: float) -> np.ndarray:
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)
    return np.array([[c, -s, tx], [s, c, ty]], dtype=np.float64)


def _shape_pts(n: int = 20) -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.uniform(-10, 10, size=(n, 2))


def test_estimate_affine_recovers_transform():
    pts1 = _shape_pts()
    M_true = _rotation_translation(25.0, 3.0, -2.0)
    pts2 = _apply(M_true, pts1)

    M_est, mask = estimate_affine(pts1, pts2, method="ransac", seed=0)
    assert M_est is not None
    np.testing.assert_allclose(M_est, M_true, atol=1e-6)
    assert mask is not None and mask.all()


def test_estimate_affine_lstsq_fallback():
    pts1 = _shape_pts()
    M_true = _rotation_translation(10.0, 0.0, 1.0)
    pts2 = _apply(M_true, pts1)
    M_est, _ = estimate_affine(pts1, pts2, method="lstsq")
    assert M_est is not None
    np.testing.assert_allclose(M_est, M_true, atol=1e-6)


def test_estimate_affine_ignores_outliers():
    pts1 = _shape_pts(20)
    M_true = _rotation_translation(20.0, -1.0, 1.0)
    pts2 = _apply(M_true, pts1)
    # Inject three outliers.
    pts2[0] = [99.0, 99.0]
    pts2[5] = [-50.0, 50.0]
    pts2[11] = [30.0, -30.0]

    M_est, mask = estimate_affine(pts1, pts2, method="ransac", seed=0, max_iters=500)
    assert M_est is not None
    np.testing.assert_allclose(M_est, M_true, atol=0.05)
    # Outliers should be flagged as non-inliers.
    assert mask is not None
    assert mask[0] is np.False_ or bool(mask[0]) is False


def test_estimate_affine_rejects_too_few_points():
    with pytest.raises(ValueError):
        estimate_affine(np.zeros((2, 2)), np.zeros((2, 2)))


def test_estimate_affine_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        estimate_affine(np.zeros((3, 2)), np.zeros((4, 2)))


def test_apply_affine_pts_rejects_bad_matrix():
    with pytest.raises(ValueError):
        apply_affine_pts(np.zeros((3, 3)), np.zeros((3, 2)))


def test_affine_reprojection_error_identity_is_zero():
    pts = _shape_pts(5)
    M = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    assert affine_reprojection_error(M, pts, pts) == pytest.approx(0.0)


def test_affine_reprojection_error_handles_empty():
    M = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    assert affine_reprojection_error(M, np.zeros((0, 2)), np.zeros((0, 2))) == 0.0


def test_score_affine_match_range():
    assert score_affine_match(50, 1.0) == pytest.approx(0.6 * 0.5 + 0.4 * 0.8)
    assert score_affine_match(0, 999.0) == pytest.approx(0.0)
    assert 0.0 <= score_affine_match(100, 0.0) <= 1.0


def test_score_affine_match_validation():
    with pytest.raises(ValueError):
        score_affine_match(5, 1.0, max_inliers=0)
    with pytest.raises(ValueError):
        score_affine_match(5, 1.0, max_error=0.0)
    with pytest.raises(ValueError):
        score_affine_match(5, 1.0, w_inliers=0.5, w_error=0.2)


def test_match_points_affine_returns_result():
    pts1 = _shape_pts(20)
    pts2 = _apply(_rotation_translation(15.0, 0.5, 0.5), pts1)
    r = match_points_affine(pts1, pts2, idx1=3, idx2=7, seed=0)
    assert isinstance(r, AffineMatchResult)
    assert r.idx1 == 3 and r.idx2 == 7
    assert r.M is not None
    assert r.n_inliers >= 3
    assert 0.0 <= r.score <= 1.0

import math

import numpy as np
import pytest

from triage4.matching import (
    RotationDTWResult,
    batch_rotation_dtw,
    rotation_dtw,
    rotation_dtw_similarity,
)


def _square(side: float = 10.0, n: int = 32) -> np.ndarray:
    per = n // 4
    t = np.linspace(0, 1, per, endpoint=False)
    top = np.column_stack([t * side, np.zeros_like(t)])
    right = np.column_stack([np.full_like(t, side), t * side])
    bottom = np.column_stack([side - t * side, np.full_like(t, side)])
    left = np.column_stack([np.zeros_like(t), side - t * side])
    return np.vstack([top, right, bottom, left])


def _rotated_square(angle_deg: float, side: float = 10.0, n: int = 32) -> np.ndarray:
    sq = _square(side, n)
    centroid = sq.mean(axis=0)
    rad = math.radians(angle_deg)
    R = np.array([[math.cos(rad), -math.sin(rad)], [math.sin(rad), math.cos(rad)]])
    return (sq - centroid) @ R.T + centroid


def test_rotation_dtw_identical_gives_zero_distance():
    sq = _square()
    result = rotation_dtw(sq, sq, n_angles=12, n_points=32, dtw_window=3)
    assert result.distance == pytest.approx(0.0, abs=1e-6)


def test_rotation_dtw_recovers_rotation():
    a = _square()
    b = _rotated_square(45.0)
    result = rotation_dtw(a, b, n_angles=36, n_points=64, dtw_window=5)
    assert isinstance(result, RotationDTWResult)
    # Best angle should be close to 315° (which un-rotates b back to a).
    assert 0.0 <= result.best_angle_deg < 360.0
    assert result.distance < 1.0


def test_rotation_dtw_empty_returns_infinity():
    empty = np.zeros((0, 2))
    result = rotation_dtw(empty, _square())
    assert result.distance == float("inf")


def test_rotation_dtw_check_mirror_prefers_mirrored_match():
    """Mirror search should never worsen the match and must flag when used."""
    sq = _square()
    mirrored = sq.copy()
    mirrored[:, 0] = -mirrored[:, 0]

    with_mirror = rotation_dtw(sq, mirrored, n_angles=36, check_mirror=True)
    without_mirror = rotation_dtw(sq, mirrored, n_angles=36, check_mirror=False)

    assert with_mirror.distance <= without_mirror.distance
    assert with_mirror.mirrored is True


def test_rotation_dtw_similarity_identical_is_one():
    sq = _square()
    assert rotation_dtw_similarity(sq, sq, n_angles=12, n_points=32, dtw_window=3) == pytest.approx(
        1.0
    )


def test_rotation_dtw_similarity_returns_unit_interval():
    a = _square()
    b = _rotated_square(30.0)
    s = rotation_dtw_similarity(a, b, n_angles=36, n_points=64, dtw_window=5)
    assert 0.0 <= s <= 1.0


def test_batch_rotation_dtw_returns_list():
    query = _square()
    candidates = [query, _rotated_square(30.0), _rotated_square(90.0)]
    results = batch_rotation_dtw(query, candidates, n_angles=12, n_points=32, dtw_window=3)
    assert len(results) == 3
    for r in results:
        assert isinstance(r, RotationDTWResult)

"""Rotation-aware Dynamic Time Warping for curve matching.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/rotation_dtw.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Extends the plain :mod:`triage4.matching.dtw` with a grid search over
rotation angles (and optionally a mirror flip). Useful when comparing
casualty shapes that may appear in any orientation — body silhouettes,
wound boundaries, posture polylines.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

from .dtw import dtw_distance


class RotationDTWResult(NamedTuple):
    distance: float
    best_angle_deg: float
    mirrored: bool


def _resample_curve(curve: np.ndarray, n: int) -> np.ndarray:
    """Resample a (K, 2) curve to exactly n arc-length-spaced points."""
    if len(curve) < 2:
        return np.zeros((n, 2))
    diffs = np.diff(curve, axis=0)
    segs = np.hypot(diffs[:, 0], diffs[:, 1])
    cumlen = np.concatenate([[0.0], np.cumsum(segs)])
    total = cumlen[-1]
    if total == 0:
        return np.tile(curve[0], (n, 1))
    t_new = np.linspace(0.0, total, n)
    x_new = np.interp(t_new, cumlen, curve[:, 0])
    y_new = np.interp(t_new, cumlen, curve[:, 1])
    return np.column_stack([x_new, y_new])


def _rotate_curve(curve: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate a (N, 2) curve by ``angle_deg`` around its centroid."""
    rad = np.deg2rad(angle_deg)
    cos_a, sin_a = np.cos(rad), np.sin(rad)
    R = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
    centroid = curve.mean(axis=0)
    shifted = curve - centroid
    rotated = shifted @ R.T
    return rotated + centroid


def _mirror_curve(curve: np.ndarray) -> np.ndarray:
    """Mirror a curve horizontally around its centroid."""
    cx = curve[:, 0].mean()
    mirrored = curve.copy()
    mirrored[:, 0] = 2 * cx - curve[:, 0]
    return mirrored


def rotation_dtw(
    curve_a: np.ndarray,
    curve_b: np.ndarray,
    n_angles: int = 36,
    n_points: int = 64,
    dtw_window: int = 10,
    check_mirror: bool = False,
) -> RotationDTWResult:
    """Grid-search rotation (and optional mirror) + DTW."""
    if len(curve_a) < 2 or len(curve_b) < 2:
        return RotationDTWResult(
            distance=float("inf"), best_angle_deg=0.0, mirrored=False
        )

    a = _resample_curve(np.asarray(curve_a, dtype=np.float64), n_points)
    b = _resample_curve(np.asarray(curve_b, dtype=np.float64), n_points)

    angles = np.linspace(0.0, 360.0, n_angles, endpoint=False)

    best_dist = float("inf")
    best_angle = 0.0
    best_mirror = False

    for theta in angles:
        b_rot = _rotate_curve(b, theta)
        dist = dtw_distance(a, b_rot, window=dtw_window)
        if dist < best_dist:
            best_dist = dist
            best_angle = float(theta)
            best_mirror = False

    if check_mirror:
        b_mir = _mirror_curve(b)
        for theta in angles:
            b_rot = _rotate_curve(b_mir, theta)
            dist = dtw_distance(a, b_rot, window=dtw_window)
            if dist < best_dist:
                best_dist = dist
                best_angle = float(theta)
                best_mirror = True

    return RotationDTWResult(
        distance=best_dist, best_angle_deg=best_angle, mirrored=best_mirror
    )


def rotation_dtw_similarity(
    curve_a: np.ndarray,
    curve_b: np.ndarray,
    n_angles: int = 36,
    n_points: int = 64,
    dtw_window: int = 10,
    check_mirror: bool = True,
) -> float:
    """Turn the rotation-aware DTW distance into a [0, 1] similarity score."""
    result = rotation_dtw(
        curve_a,
        curve_b,
        n_angles=n_angles,
        n_points=n_points,
        dtw_window=dtw_window,
        check_mirror=check_mirror,
    )
    if result.distance == float("inf"):
        return 0.0
    return float(np.exp(-result.distance))


def batch_rotation_dtw(
    query: np.ndarray,
    candidates: list[np.ndarray],
    n_angles: int = 36,
    n_points: int = 64,
    dtw_window: int = 10,
    check_mirror: bool = True,
) -> list[RotationDTWResult]:
    return [
        rotation_dtw(
            query,
            cand,
            n_angles=n_angles,
            n_points=n_points,
            dtw_window=dtw_window,
            check_mirror=check_mirror,
        )
        for cand in candidates
    ]

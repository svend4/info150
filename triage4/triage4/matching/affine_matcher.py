"""Affine transform estimation for 2D point pairs.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/affine_matcher.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- The upstream module uses OpenCV (`cv2.estimateAffine2D`, ORB features,
  BFMatcher) to run a full pipeline from images to an affine match. To
  keep triage4 dependency-light we only port the *geometry* side (point →
  point) and implement RANSAC in pure numpy. The image-to-image pipeline
  (`match_fragments_affine`, `batch_affine_match`) is left for a future
  round that opts into OpenCV.
- `estimate_affine`, `apply_affine_pts`, `affine_reprojection_error` and
  `score_affine_match` keep the upstream API.
- Used in triage4 to align two posture silhouettes or two wound point
  clouds across frames (e.g. to quantify drift).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np


@dataclass
class AffineMatchResult:
    idx1: int
    idx2: int
    M: Optional[np.ndarray]
    n_inliers: int
    reprojection_error: float
    score: float
    params: dict = field(default_factory=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"AffineMatchResult(idx1={self.idx1}, idx2={self.idx2}, "
            f"inliers={self.n_inliers}, score={self.score:.4f})"
        )


def _solve_affine_from_3(pts1: np.ndarray, pts2: np.ndarray) -> Optional[np.ndarray]:
    """Closed-form affine transform from 3 point pairs via np.linalg.solve."""
    a = np.zeros((6, 6), dtype=np.float64)
    b = np.zeros(6, dtype=np.float64)
    for i in range(3):
        x, y = pts1[i]
        u, v = pts2[i]
        a[2 * i] = [x, y, 1, 0, 0, 0]
        a[2 * i + 1] = [0, 0, 0, x, y, 1]
        b[2 * i] = u
        b[2 * i + 1] = v
    try:
        h = np.linalg.solve(a, b)
    except np.linalg.LinAlgError:
        return None
    return np.array([[h[0], h[1], h[2]], [h[3], h[4], h[5]]], dtype=np.float64)


def _least_squares_affine(
    pts1: np.ndarray, pts2: np.ndarray
) -> Optional[np.ndarray]:
    """Least-squares affine transform from arbitrary number of pairs."""
    n = len(pts1)
    if n < 3:
        return None
    a = np.zeros((2 * n, 6), dtype=np.float64)
    b = np.zeros(2 * n, dtype=np.float64)
    for i in range(n):
        x, y = pts1[i]
        u, v = pts2[i]
        a[2 * i] = [x, y, 1, 0, 0, 0]
        a[2 * i + 1] = [0, 0, 0, x, y, 1]
        b[2 * i] = u
        b[2 * i + 1] = v
    h, *_ = np.linalg.lstsq(a, b, rcond=None)
    return np.array([[h[0], h[1], h[2]], [h[3], h[4], h[5]]], dtype=np.float64)


def estimate_affine(
    pts1: np.ndarray,
    pts2: np.ndarray,
    method: str = "ransac",
    ransac_threshold: float = 3.0,
    max_iters: int = 200,
    seed: int | None = 0,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Estimate a 2×3 affine transform from point correspondences.

    ``method='ransac'`` runs a simple RANSAC loop in pure Python; ``'lstsq'``
    falls back to least-squares using all points. Returns ``(M, inlier_mask)``.
    """
    if method not in ("ransac", "lstsq"):
        raise ValueError(f"method must be 'ransac' or 'lstsq', got {method!r}")
    p1 = np.asarray(pts1, dtype=np.float64).reshape(-1, 2)
    p2 = np.asarray(pts2, dtype=np.float64).reshape(-1, 2)
    if p1.shape != p2.shape:
        raise ValueError(
            f"pts1 and pts2 must have the same shape, got {p1.shape} vs {p2.shape}"
        )
    if len(p1) < 3:
        raise ValueError(f"at least 3 point pairs are required, got {len(p1)}")

    if method == "lstsq":
        M = _least_squares_affine(p1, p2)
        if M is None:
            return None, None
        errors = np.linalg.norm(apply_affine_pts(M, p1) - p2, axis=1)
        mask = errors <= ransac_threshold
        return M, mask

    rng = random.Random(seed)
    n = len(p1)
    best_M: Optional[np.ndarray] = None
    best_inliers: Optional[np.ndarray] = None
    best_count = -1

    for _ in range(max_iters):
        sample_idx = rng.sample(range(n), 3)
        M_sample = _solve_affine_from_3(p1[sample_idx], p2[sample_idx])
        if M_sample is None:
            continue
        errors = np.linalg.norm(apply_affine_pts(M_sample, p1) - p2, axis=1)
        inliers = errors <= ransac_threshold
        count = int(inliers.sum())
        if count > best_count:
            best_count = count
            best_inliers = inliers
            best_M = M_sample

    if best_M is None or best_inliers is None or best_count < 3:
        return None, None

    # Refine with least-squares on inliers.
    refined = _least_squares_affine(p1[best_inliers], p2[best_inliers])
    if refined is not None:
        best_M = refined
        errors = np.linalg.norm(apply_affine_pts(best_M, p1) - p2, axis=1)
        best_inliers = errors <= ransac_threshold

    return best_M, best_inliers


def apply_affine_pts(M: np.ndarray, pts: np.ndarray) -> np.ndarray:
    M_arr = np.asarray(M, dtype=np.float64)
    if M_arr.shape != (2, 3):
        raise ValueError(f"M must have shape (2, 3), got {M_arr.shape}")
    p = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
    ones = np.ones((len(p), 1), dtype=np.float64)
    ph = np.hstack([p, ones])
    return (M_arr @ ph.T).T


def affine_reprojection_error(
    M: np.ndarray,
    pts1: np.ndarray,
    pts2: np.ndarray,
    inlier_mask: Optional[np.ndarray] = None,
) -> float:
    p1 = np.asarray(pts1, dtype=np.float64).reshape(-1, 2)
    p2 = np.asarray(pts2, dtype=np.float64).reshape(-1, 2)
    if p1.shape != p2.shape:
        raise ValueError(
            f"pts1 and pts2 shapes must match, got {p1.shape} vs {p2.shape}"
        )
    if len(p1) == 0:
        return 0.0
    projected = apply_affine_pts(M, p1)
    errors = np.linalg.norm(projected - p2, axis=1)
    if inlier_mask is not None:
        mask = np.asarray(inlier_mask, dtype=bool)
        if mask.sum() == 0:
            return 0.0
        errors = errors[mask]
    return float(errors.mean())


def score_affine_match(
    n_inliers: int,
    reprojection_error: float,
    max_inliers: int = 100,
    max_error: float = 5.0,
    w_inliers: float = 0.6,
    w_error: float = 0.4,
) -> float:
    if max_inliers <= 0:
        raise ValueError(f"max_inliers must be > 0, got {max_inliers}")
    if max_error <= 0:
        raise ValueError(f"max_error must be > 0, got {max_error}")
    if abs(w_inliers + w_error - 1.0) > 0.01:
        raise ValueError(
            f"w_inliers + w_error must sum to 1.0, got {w_inliers + w_error:.4f}"
        )
    inlier_score = min(float(n_inliers) / max_inliers, 1.0)
    error_score = max(0.0, 1.0 - reprojection_error / max_error)
    return float(w_inliers * inlier_score + w_error * error_score)


def match_points_affine(
    pts1: np.ndarray,
    pts2: np.ndarray,
    idx1: int = 0,
    idx2: int = 1,
    ransac_threshold: float = 3.0,
    max_inliers: int = 100,
    max_error: float = 5.0,
    seed: int | None = 0,
) -> AffineMatchResult:
    """Geometry-only affine pipeline for two point clouds.

    This replaces upstream's cv2-based ``match_fragments_affine`` when
    callers already have point correspondences (e.g. tracked body
    keypoints across frames).
    """
    params = {
        "ransac_threshold": ransac_threshold,
        "max_inliers": max_inliers,
        "max_error": max_error,
    }
    M, mask = estimate_affine(
        pts1, pts2, method="ransac", ransac_threshold=ransac_threshold, seed=seed
    )
    if M is None:
        return AffineMatchResult(
            idx1=idx1,
            idx2=idx2,
            M=None,
            n_inliers=0,
            reprojection_error=0.0,
            score=0.0,
            params=params,
        )
    n_in = int(mask.sum()) if mask is not None else len(pts1)
    err = affine_reprojection_error(M, pts1, pts2, mask)
    score = score_affine_match(
        n_in, err, max_inliers=max_inliers, max_error=max_error
    )
    return AffineMatchResult(
        idx1=idx1,
        idx2=idx2,
        M=M,
        n_inliers=n_in,
        reprojection_error=err,
        score=score,
        params=params,
    )

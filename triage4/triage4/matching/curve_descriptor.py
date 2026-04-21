"""Compact Fourier descriptor of an ordered 2D curve.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/curve_descriptor.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Copied verbatim. Upstream compares torn-document edge curves; triage4
  applies the same descriptor to wound/posture silhouettes and to 2D
  chest-motion polylines (``(t, amplitude)`` trajectories).
- Translation, rotation and scale invariance is optional via the
  ``normalize`` / ``center`` flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class CurveDescriptorConfig:
    n_harmonics: int = 8
    normalize: bool = True
    center: bool = True
    resample_n: Optional[int] = None

    def __post_init__(self) -> None:
        if self.n_harmonics < 1:
            raise ValueError(f"n_harmonics must be >= 1, got {self.n_harmonics}")
        if self.resample_n is not None and self.resample_n < 2:
            raise ValueError(
                f"resample_n must be >= 2 or None, got {self.resample_n}"
            )


@dataclass
class CurveDescriptor:
    fourier_desc: np.ndarray
    arc_length: float
    curvature_mean: float
    curvature_std: float
    n_points: int

    def __post_init__(self) -> None:
        if self.arc_length < 0.0:
            raise ValueError(f"arc_length must be >= 0, got {self.arc_length}")
        if self.n_points < 0:
            raise ValueError(f"n_points must be >= 0, got {self.n_points}")

    def __repr__(self) -> str:
        return (
            f"CurveDescriptor(n_harmonics={len(self.fourier_desc)}, "
            f"arc_length={self.arc_length:.2f}, n_points={self.n_points})"
        )


def compute_fourier_descriptor(
    curve: np.ndarray,
    n_harmonics: int = 8,
    normalize: bool = True,
    center: bool = True,
) -> np.ndarray:
    """Amplitude Fourier descriptor of an ordered (N, 2) curve."""
    pts = np.asarray(curve, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"curve must have shape (N, 2), got {pts.shape}")
    if len(pts) == 0:
        return np.zeros(n_harmonics, dtype=np.float64)

    z = pts[:, 0] + 1j * pts[:, 1]
    if center:
        z = z - z.mean()

    Z = np.fft.fft(z)
    amplitudes = np.abs(Z)

    n = len(amplitudes)
    n_take = min(n_harmonics, n - 1)
    desc = amplitudes[1 : n_take + 1]

    if len(desc) < n_harmonics:
        desc = np.pad(desc, (0, n_harmonics - len(desc)))

    if normalize and desc[0] > 1e-9:
        desc = desc / desc[0]

    return desc.astype(np.float64)


def compute_curvature_profile(curve: np.ndarray) -> np.ndarray:
    """Signed discrete curvature along an ordered 2D polyline."""
    pts = np.asarray(curve, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"curve must have shape (N, 2), got {pts.shape}")
    n = len(pts)
    if n < 3:
        return np.zeros(n, dtype=np.float64)

    curv = np.zeros(n, dtype=np.float64)
    for i in range(1, n - 1):
        v1 = pts[i] - pts[i - 1]
        v2 = pts[i + 1] - pts[i]
        l1 = np.linalg.norm(v1)
        l2 = np.linalg.norm(v2)
        if l1 < 1e-12 or l2 < 1e-12:
            continue
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        curv[i] = cross / (l1 * l2)

    return curv


def describe_curve(
    curve: np.ndarray, cfg: Optional[CurveDescriptorConfig] = None
) -> CurveDescriptor:
    if cfg is None:
        cfg = CurveDescriptorConfig()

    pts = np.asarray(curve, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"curve must have shape (N, 2), got {pts.shape}")

    n_pts = len(pts)
    if cfg.resample_n is not None and n_pts >= 2:
        pts = _resample_curve(pts, cfg.resample_n)

    if len(pts) >= 2:
        diffs = np.diff(pts, axis=0)
        arc_len = float(np.linalg.norm(diffs, axis=1).sum())
    else:
        arc_len = 0.0

    curv = compute_curvature_profile(pts)
    abs_curv = np.abs(curv)
    curv_mean = float(abs_curv.mean()) if len(abs_curv) > 0 else 0.0
    curv_std = float(abs_curv.std()) if len(abs_curv) > 0 else 0.0

    fd = compute_fourier_descriptor(
        pts,
        n_harmonics=cfg.n_harmonics,
        normalize=cfg.normalize,
        center=cfg.center,
    )

    return CurveDescriptor(
        fourier_desc=fd,
        arc_length=arc_len,
        curvature_mean=curv_mean,
        curvature_std=curv_std,
        n_points=n_pts,
    )


def descriptor_distance(d1: CurveDescriptor, d2: CurveDescriptor) -> float:
    v1 = d1.fourier_desc
    v2 = d2.fourier_desc
    n = min(len(v1), len(v2))
    if n == 0:
        return 0.0
    return float(np.linalg.norm(v1[:n] - v2[:n]))


def descriptor_similarity(
    d1: CurveDescriptor, d2: CurveDescriptor, sigma: float = 1.0
) -> float:
    if sigma <= 0.0:
        raise ValueError(f"sigma must be > 0, got {sigma}")
    dist = descriptor_distance(d1, d2)
    return float(np.exp(-(dist ** 2) / (2.0 * sigma ** 2)))


def batch_describe_curves(
    curves: List[np.ndarray], cfg: Optional[CurveDescriptorConfig] = None
) -> List[CurveDescriptor]:
    if cfg is None:
        cfg = CurveDescriptorConfig()
    return [describe_curve(c, cfg) for c in curves]


def find_best_match(
    query: CurveDescriptor, candidates: List[CurveDescriptor]
) -> Tuple[int, float]:
    if not candidates:
        raise ValueError("candidates must not be empty")

    best_idx = 0
    best_dist = descriptor_distance(query, candidates[0])
    for i, c in enumerate(candidates[1:], start=1):
        d = descriptor_distance(query, c)
        if d < best_dist:
            best_dist = d
            best_idx = i

    return (best_idx, best_dist)


def _resample_curve(pts: np.ndarray, n: int) -> np.ndarray:
    dists = np.concatenate(
        [[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    )
    total = dists[-1]
    if total < 1e-12:
        return np.tile(pts[0], (n, 1))
    t_new = np.linspace(0.0, total, n)
    xs = np.interp(t_new, dists, pts[:, 0])
    ys = np.interp(t_new, dists, pts[:, 1])
    return np.column_stack([xs, ys])

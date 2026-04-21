"""Box-counting fractal dimension.

Adapted from svend4/meta2 — ``puzzle_reconstruction/algorithms/fractal/box_counting.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Signature is kept (Nx2 contour, not a binary mask) to match the upstream.
- A small ``mask_to_contour`` helper is provided to convert triage4's
  wound/thermal masks into the (N, 2) point contour the algorithm expects.
- Russian docstrings are preserved for traceability against upstream.
"""

from __future__ import annotations

import numpy as np


def box_counting_fd(contour: np.ndarray, n_scales: int = 8) -> float:
    """
    Вычисляет фрактальную размерность контура методом Box-counting.

    Args:
        contour:  (N, 2) координаты точек контура.
        n_scales: Число масштабов (степени 2).

    Returns:
        FD ∈ [1.0, 2.0] — фрактальная размерность.
        1.0 = гладкая линия, 2.0 = заполняет плоскость.
    """
    pts = np.asarray(contour, dtype=np.float64)
    if len(pts) < 4:
        return 1.0

    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    span = (maxs - mins).max()
    if span == 0:
        return 1.0
    pts_norm = (pts - mins) / span

    log_r_inv: list[float] = []
    log_N: list[float] = []

    for k in range(1, n_scales + 1):
        n_bins = 2 ** k
        ix = np.floor(pts_norm[:, 0] * n_bins).astype(np.int32)
        iy = np.floor(pts_norm[:, 1] * n_bins).astype(np.int32)
        ix = np.clip(ix, 0, n_bins - 1)
        iy = np.clip(iy, 0, n_bins - 1)

        n_occupied = len(set(zip(ix.tolist(), iy.tolist())))
        if n_occupied <= 0:
            continue
        log_r_inv.append(float(np.log2(n_bins)))
        log_N.append(float(np.log2(n_occupied)))

    if len(log_r_inv) < 2:
        return 1.0

    fd = float(np.polyfit(log_r_inv, log_N, 1)[0])
    return float(np.clip(fd, 1.0, 2.0))


def box_counting_curve(
    contour: np.ndarray, n_scales: int = 8
) -> tuple[np.ndarray, np.ndarray]:
    """
    Возвращает полную кривую log(N) vs log(1/r) для визуализации.
    """
    pts = np.asarray(contour, dtype=np.float64)
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    span = (maxs - mins).max()
    if span == 0 or len(pts) < 2:
        return np.zeros(n_scales), np.zeros(n_scales)
    pts_norm = (pts - mins) / span

    log_r_inv, log_N = [], []
    for k in range(1, n_scales + 1):
        n_bins = 2 ** k
        ix = np.clip(np.floor(pts_norm[:, 0] * n_bins).astype(np.int32), 0, n_bins - 1)
        iy = np.clip(np.floor(pts_norm[:, 1] * n_bins).astype(np.int32), 0, n_bins - 1)
        n_occupied = len(set(zip(ix.tolist(), iy.tolist())))
        log_r_inv.append(float(np.log2(n_bins)))
        log_N.append(float(np.log2(max(n_occupied, 1))))

    return np.array(log_r_inv), np.array(log_N)


def mask_to_contour(mask) -> np.ndarray:
    """Convert a 2D binary mask into an (N, 2) array of occupied pixel coords.

    Not part of upstream meta2 — triage4-specific helper so existing callers
    that have a mask (wound / thermal anomaly region) can feed the contour
    algorithms.
    """
    m = np.asarray(mask)
    if m.ndim != 2 or m.size == 0:
        return np.zeros((0, 2), dtype=np.float64)
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return np.zeros((0, 2), dtype=np.float64)
    return np.column_stack([xs, ys]).astype(np.float64)


class BoxCountingFD:
    """Object-oriented facade around ``box_counting_fd`` for triage4 internals."""

    def __init__(self, n_scales: int = 8) -> None:
        self.n_scales = int(n_scales)

    def estimate(self, contour_or_mask) -> float:
        arr = np.asarray(contour_or_mask)
        if arr.ndim == 2 and arr.shape[1] == 2:
            return box_counting_fd(arr, self.n_scales)
        contour = mask_to_contour(arr)
        if len(contour) < 4:
            return 0.0
        return box_counting_fd(contour, self.n_scales)

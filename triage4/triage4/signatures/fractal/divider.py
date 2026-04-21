"""Richardson-divider fractal dimension.

Adapted from svend4/meta2 — ``puzzle_reconstruction/algorithms/fractal/divider.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Upstream signature preserved (Nx2 ordered contour points).
- A small helper ``signal_to_contour`` turns a 1D triage signal (e.g. a
  chest-motion curve) into an (i, v) polyline so the same algorithm works.
"""

from __future__ import annotations

from typing import Iterable, Tuple

import numpy as np


def divider_fd(contour: np.ndarray, n_scales: int = 8) -> float:
    """Фрактальная размерность методом Divider."""
    log_s, log_L = divider_curve(contour, n_scales)
    if len(log_s) < 2:
        return 1.0
    slope = float(np.polyfit(log_s, log_L, 1)[0])
    fd = 1.0 - slope
    return float(np.clip(fd, 1.0, 2.0))


def divider_curve(
    contour: np.ndarray, n_scales: int = 8
) -> Tuple[np.ndarray, np.ndarray]:
    """Кривая log(L) vs log(s) методом компаса."""
    pts = np.asarray(contour, dtype=np.float64)

    if len(pts) < 2:
        return np.array([]), np.array([])

    seg_len = float(np.hypot(np.diff(pts[:, 0]), np.diff(pts[:, 1])).sum())
    if seg_len == 0:
        return np.array([]), np.array([])

    s_min = seg_len * 0.005
    s_max = seg_len * 0.15
    if s_min >= s_max:
        return np.array([]), np.array([])
    steps = np.geomspace(s_min, s_max, n_scales)

    log_s: list[float] = []
    log_L: list[float] = []

    for s in steps:
        count = _walk_with_step(pts, float(s))
        if count > 1:
            log_s.append(float(np.log(s)))
            log_L.append(float(np.log(count * s)))

    return np.array(log_s), np.array(log_L)


def _walk_with_step(pts: np.ndarray, step: float) -> int:
    """Шаг компаса вдоль контура — возвращает число шагов."""
    if len(pts) < 2:
        return 0

    count = 0
    current = pts[0].copy()
    idx = 0

    while idx < len(pts) - 1:
        remaining = step
        while idx < len(pts) - 1 and remaining > 0:
            d = float(
                np.hypot(pts[idx + 1, 0] - current[0], pts[idx + 1, 1] - current[1])
            )
            if d <= remaining:
                remaining -= d
                current = pts[idx + 1].copy()
                idx += 1
            else:
                t = remaining / d
                current = current + t * (pts[idx + 1] - current)
                remaining = 0
        count += 1

    return count


def signal_to_contour(signal: Iterable[float]) -> np.ndarray:
    """Turn a 1D triage signal into a 2D polyline ``[(i, v)]``.

    Not part of upstream meta2. Useful so the compass algorithm can be
    applied to chest-motion curves and similar 1D triage signals.
    """
    vals = np.asarray(list(signal), dtype=np.float64)
    xs = np.arange(len(vals), dtype=np.float64)
    return np.column_stack([xs, vals])


class RichardsonDivider:
    """Object-oriented facade used by triage4 for motion analysis."""

    def __init__(self, n_scales: int = 8) -> None:
        self.n_scales = int(n_scales)

    def estimate(self, contour: np.ndarray) -> float:
        return divider_fd(np.asarray(contour), self.n_scales)

    def estimate_1d(self, signal: Iterable[float]) -> float:
        contour = signal_to_contour(signal)
        if len(contour) < 4:
            return 0.0
        return divider_fd(contour, self.n_scales)

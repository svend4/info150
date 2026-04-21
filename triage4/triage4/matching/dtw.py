"""Dynamic Time Warping.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/dtw.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Upstream uses DTW to compare torn-document edge curves. Here it compares
  temporal triage signals (chest-motion, perfusion, …) across frames.
- Sakoe-Chiba window preserved.
"""

from __future__ import annotations

import numpy as np


def dtw_distance(a: np.ndarray, b: np.ndarray, window: int = 20) -> float:
    """
    DTW-расстояние между двумя параметрическими кривыми.

    Args:
        a: (N, D) — кривая A.
        b: (M, D) — кривая B.
        window: Ширина окна Сакое-Чибы.

    Returns:
        dist: нормализованное DTW-расстояние.
    """
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    if a_arr.ndim == 1:
        a_arr = a_arr[:, None]
    if b_arr.ndim == 1:
        b_arr = b_arr[:, None]

    n, m = len(a_arr), len(b_arr)
    if n == 0 or m == 0:
        return float("inf")

    w = max(window, abs(n - m))

    dtw = np.full((n + 1, m + 1), np.inf)
    dtw[0, 0] = 0.0

    for i in range(1, n + 1):
        j_lo = max(1, i - w)
        j_hi = min(m, i + w)
        for j in range(j_lo, j_hi + 1):
            cost = float(np.linalg.norm(a_arr[i - 1] - b_arr[j - 1]))
            dtw[i, j] = cost + min(dtw[i - 1, j], dtw[i, j - 1], dtw[i - 1, j - 1])

    raw = dtw[n, m]
    return float(raw / (n + m)) if (n + m) > 0 else 0.0


def dtw_distance_mirror(a: np.ndarray, b: np.ndarray, window: int = 20) -> float:
    """DTW устойчивое к зеркальному отражению (min прямого и обратного)."""
    d_direct = dtw_distance(a, b, window)
    d_mirror = dtw_distance(a, np.asarray(b)[::-1], window)
    return min(d_direct, d_mirror)

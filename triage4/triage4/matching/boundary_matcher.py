"""Boundary / shape matching via Hausdorff, Chamfer and Fréchet distances.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/boundary_matcher.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Upstream is about matching torn-document edges that come from rectangular
  fragments and therefore carry a ``side ∈ {0, 1, 2, 3}`` (top/right/bottom/left).
- triage4 keeps the upstream 4-sides API for traceability but mostly uses
  the underlying distance functions directly through the triage-specific
  ``shape_match`` module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class BoundaryMatch:
    """Результат сравнения граничных контуров двух сущностей."""

    idx1: int
    idx2: int
    side1: int
    side2: int
    hausdorff: float
    chamfer: float
    frechet: float
    total_score: float
    params: Dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"BoundaryMatch(idx1={self.idx1}, idx2={self.idx2}, "
            f"side1={self.side1}, side2={self.side2}, "
            f"total={self.total_score:.3f})"
        )


def extract_boundary_points(
    contour: np.ndarray, side: int, n_points: int = 50
) -> np.ndarray:
    """Выбирает n_points точек вдоль указанной стороны bbox контура."""
    if side not in (0, 1, 2, 3):
        raise ValueError(f"side must be 0..3, got {side!r}")

    pts = np.asarray(contour).reshape(-1, 2).astype(np.float64)
    if pts.size == 0:
        raise ValueError("contour must not be empty")

    if side == 0:
        axis, reverse = 1, False
    elif side == 1:
        axis, reverse = 0, True
    elif side == 2:
        axis, reverse = 1, True
    else:
        axis, reverse = 0, False

    k = max(1, len(pts) // 5)
    edge_vals = pts[:, axis]
    if reverse:
        idx_sort = np.argsort(-edge_vals)
    else:
        idx_sort = np.argsort(edge_vals)
    edge_pts = pts[idx_sort[:k]]

    if len(edge_pts) <= n_points:
        selected = edge_pts
    else:
        indices = np.round(np.linspace(0, len(edge_pts) - 1, n_points)).astype(int)
        selected = edge_pts[indices]

    if len(selected) < n_points:
        repeat = np.tile(selected[-1:], (n_points - len(selected), 1))
        selected = np.vstack([selected, repeat])

    return selected[:n_points]


def hausdorff_distance(pts1: np.ndarray, pts2: np.ndarray) -> float:
    """Симметричное расстояние Хаусдорфа между двумя облаками точек."""
    a = np.asarray(pts1, dtype=np.float64)
    b = np.asarray(pts2, dtype=np.float64)
    if a.size == 0 or b.size == 0:
        return 0.0
    diff = a[:, None, :] - b[None, :, :]
    dist = np.linalg.norm(diff, axis=-1)
    d_12 = dist.min(axis=1).max()
    d_21 = dist.min(axis=0).max()
    return float(max(d_12, d_21))


def chamfer_distance(pts1: np.ndarray, pts2: np.ndarray) -> float:
    """Симметричное расстояние Чамфера."""
    a = np.asarray(pts1, dtype=np.float64)
    b = np.asarray(pts2, dtype=np.float64)
    if a.size == 0 or b.size == 0:
        return 0.0
    diff = a[:, None, :] - b[None, :, :]
    dist = np.linalg.norm(diff, axis=-1)
    c_12 = dist.min(axis=1).mean()
    c_21 = dist.min(axis=0).mean()
    return float((c_12 + c_21) / 2.0)


def frechet_approx(pts1: np.ndarray, pts2: np.ndarray) -> float:
    """Дискретное расстояние Фреше через DP (ограничено 30 точками)."""
    a = np.asarray(pts1, dtype=np.float64)
    b = np.asarray(pts2, dtype=np.float64)
    if a.size == 0 or b.size == 0:
        return 0.0

    MAX_PTS = 30
    n, m = len(a), len(b)
    if n > MAX_PTS or m > MAX_PTS:
        idx1 = np.round(np.linspace(0, n - 1, MAX_PTS)).astype(int)
        idx2 = np.round(np.linspace(0, m - 1, MAX_PTS)).astype(int)
        a = a[idx1]
        b = b[idx2]
        n, m = MAX_PTS, MAX_PTS

    ca = np.full((n, m), -1.0, dtype=np.float64)

    def _dist(i: int, j: int) -> float:
        return float(np.linalg.norm(a[i] - b[j]))

    def _c(i: int, j: int) -> float:
        if ca[i, j] > -1.0:
            return float(ca[i, j])
        d = _dist(i, j)
        if i == 0 and j == 0:
            ca[i, j] = d
        elif i == 0:
            ca[i, j] = max(_c(0, j - 1), d)
        elif j == 0:
            ca[i, j] = max(_c(i - 1, 0), d)
        else:
            ca[i, j] = max(min(_c(i - 1, j), _c(i - 1, j - 1), _c(i, j - 1)), d)
        return float(ca[i, j])

    return _c(n - 1, m - 1)


def score_boundary_pair(
    pts1: np.ndarray,
    pts2: np.ndarray,
    max_dist: float = 100.0,
    weights: Optional[Tuple[float, float, float]] = None,
) -> Tuple[float, float, float, float]:
    """Нормированные оценки [0, 1] для пары облаков точек.

    ``score_x = exp(-distance_x / max_dist)``; total — взвешенное среднее.
    """
    max_d = max(max_dist, 1e-9)

    h_dist = hausdorff_distance(pts1, pts2)
    c_dist = chamfer_distance(pts1, pts2)
    f_dist = frechet_approx(pts1, pts2)

    h_score = float(np.exp(-h_dist / max_d))
    c_score = float(np.exp(-c_dist / max_d))
    f_score = float(np.exp(-f_dist / max_d))

    if weights is None:
        wh, wc, wf = 1.0 / 3, 1.0 / 3, 1.0 / 3
    else:
        wh, wc, wf = weights
        s = wh + wc + wf
        if s > 1e-9:
            wh /= s
            wc /= s
            wf /= s

    total = float(np.clip(wh * h_score + wc * c_score + wf * f_score, 0.0, 1.0))
    return h_score, c_score, f_score, total


def match_boundary_pair(
    contour1: np.ndarray,
    contour2: np.ndarray,
    idx1: int = 0,
    idx2: int = 1,
    side1: int = 2,
    side2: int = 0,
    n_points: int = 50,
    max_dist: float = 100.0,
    weights: Optional[Tuple[float, float, float]] = None,
) -> BoundaryMatch:
    """Сопоставляет границы двух фрагментов (по выбранным сторонам bbox)."""
    pts1 = extract_boundary_points(contour1, side1, n_points)
    pts2 = extract_boundary_points(contour2, side2, n_points)

    h_score, c_score, f_score, total = score_boundary_pair(
        pts1, pts2, max_dist=max_dist, weights=weights
    )

    return BoundaryMatch(
        idx1=idx1,
        idx2=idx2,
        side1=side1,
        side2=side2,
        hausdorff=h_score,
        chamfer=c_score,
        frechet=f_score,
        total_score=total,
        params={"n_points": n_points, "max_dist": max_dist, "weights": weights},
    )


def batch_match_boundaries(
    contours: List[np.ndarray],
    pairs: List[Tuple[int, int]],
    side_pairs: Optional[List[Tuple[int, int]]] = None,
    n_points: int = 50,
    max_dist: float = 100.0,
    weights: Optional[Tuple[float, float, float]] = None,
) -> List[BoundaryMatch]:
    """Пакетное сопоставление границ."""
    if not pairs:
        return []

    if side_pairs is None:
        side_pairs = [(2, 0)] * len(pairs)

    return [
        match_boundary_pair(
            contours[i1],
            contours[i2],
            idx1=i1,
            idx2=i2,
            side1=s1,
            side2=s2,
            n_points=n_points,
            max_dist=max_dist,
            weights=weights,
        )
        for (i1, i2), (s1, s2) in zip(pairs, side_pairs)
    ]

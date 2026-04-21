"""Geometric shape matching (area / aspect / Hu-moments).

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/geometric_match.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Upstream uses OpenCV (``cv2``) to compute ``FragmentGeometry`` from a
  binary mask. To keep triage4's dependency footprint light we skip the
  OpenCV-based helper and instead provide ``compute_geometry_from_contour``
  that takes an ``(N, 2)`` contour (in image coords) and computes the same
  properties in pure numpy.
- The similarity functions (``aspect_ratio_similarity``,
  ``area_ratio_similarity``, ``hu_moments_similarity``) and the
  composite ``match_geometry`` are ported verbatim.
- For masks, use ``triage4.signatures.fractal.mask_to_contour`` first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class FragmentGeometry:
    """Geometric profile of a single region."""

    area: float
    perimeter: float
    aspect_ratio: float
    hull_area: float
    solidity: float
    hu_moments: np.ndarray
    bbox: Tuple[int, int, int, int]
    params: Dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"FragmentGeometry(area={self.area:.1f}, "
            f"ar={self.aspect_ratio:.2f}, "
            f"solidity={self.solidity:.2f})"
        )


@dataclass
class GeometricMatchResult:
    score: float
    aspect_score: float
    area_score: float
    hu_score: float
    method: str = "geometric"
    params: Dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"GeometricMatchResult(score={self.score:.3f}, "
            f"aspect={self.aspect_score:.3f}, "
            f"area={self.area_score:.3f}, "
            f"hu={self.hu_score:.3f})"
        )


# --- pure-numpy geometry computation (triage4 replacement for the cv2 path) --


def _polygon_area(pts: np.ndarray) -> float:
    """Shoelace area of a closed polygon (points assumed ordered)."""
    x = pts[:, 0]
    y = pts[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _polygon_perimeter(pts: np.ndarray) -> float:
    diffs = np.diff(np.vstack([pts, pts[:1]]), axis=0)
    return float(np.linalg.norm(diffs, axis=1).sum())


def _convex_hull_area(pts: np.ndarray) -> float:
    """Convex hull area via monotone chain, pure-numpy."""
    if len(pts) < 3:
        return 0.0
    order = np.lexsort((pts[:, 1], pts[:, 0]))
    sorted_pts = pts[order]

    def _cross(o: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
        return float((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]))

    lower: list[np.ndarray] = []
    for p in sorted_pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[np.ndarray] = []
    for p in reversed(sorted_pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = np.asarray(lower[:-1] + upper[:-1])
    if len(hull) < 3:
        return 0.0
    return _polygon_area(hull)


def _hu_moments(pts: np.ndarray) -> np.ndarray:
    """Seven Hu invariants, log-normalised, computed on a point cloud.

    This is a lightweight approximation: we treat the contour as uniform
    mass at each vertex. Good enough for triage-grade shape comparison.
    """
    if len(pts) == 0:
        return np.zeros(7, dtype=np.float64)

    x = pts[:, 0].astype(np.float64)
    y = pts[:, 1].astype(np.float64)
    m00 = float(len(pts))
    if m00 == 0:
        return np.zeros(7, dtype=np.float64)

    xc = x.mean()
    yc = y.mean()
    x0 = x - xc
    y0 = y - yc

    def mu(p: int, q: int) -> float:
        return float(np.sum((x0 ** p) * (y0 ** q)))

    mu20 = mu(2, 0)
    mu02 = mu(0, 2)
    mu11 = mu(1, 1)
    mu30 = mu(3, 0)
    mu03 = mu(0, 3)
    mu21 = mu(2, 1)
    mu12 = mu(1, 2)

    def eta(p: int, q: int, mu_pq: float) -> float:
        return mu_pq / (m00 ** (1 + (p + q) / 2.0)) if m00 > 0 else 0.0

    n20 = eta(2, 0, mu20)
    n02 = eta(0, 2, mu02)
    n11 = eta(1, 1, mu11)
    n30 = eta(3, 0, mu30)
    n03 = eta(0, 3, mu03)
    n21 = eta(2, 1, mu21)
    n12 = eta(1, 2, mu12)

    h1 = n20 + n02
    h2 = (n20 - n02) ** 2 + 4 * n11 ** 2
    h3 = (n30 - 3 * n12) ** 2 + (3 * n21 - n03) ** 2
    h4 = (n30 + n12) ** 2 + (n21 + n03) ** 2
    h5 = (n30 - 3 * n12) * (n30 + n12) * (
        (n30 + n12) ** 2 - 3 * (n21 + n03) ** 2
    ) + (3 * n21 - n03) * (n21 + n03) * (
        3 * (n30 + n12) ** 2 - (n21 + n03) ** 2
    )
    h6 = (n20 - n02) * ((n30 + n12) ** 2 - (n21 + n03) ** 2) + 4 * n11 * (
        n30 + n12
    ) * (n21 + n03)
    h7 = (3 * n21 - n03) * (n30 + n12) * (
        (n30 + n12) ** 2 - 3 * (n21 + n03) ** 2
    ) - (n30 - 3 * n12) * (n21 + n03) * (
        3 * (n30 + n12) ** 2 - (n21 + n03) ** 2
    )

    hu = np.array([h1, h2, h3, h4, h5, h6, h7], dtype=np.float64)
    hu_log = np.sign(hu) * np.log10(np.abs(hu) + 1e-10)
    return hu_log


def compute_geometry_from_contour(
    contour: np.ndarray, epsilon_frac: float = 0.02
) -> FragmentGeometry:
    """Compute a FragmentGeometry from an ``(N, 2)`` contour in pure numpy."""
    pts = np.asarray(contour, dtype=np.float64).reshape(-1, 2)
    zero7 = np.zeros(7, dtype=np.float64)

    if len(pts) < 3:
        return FragmentGeometry(
            area=0.0,
            perimeter=0.0,
            aspect_ratio=1.0,
            hull_area=0.0,
            solidity=0.0,
            hu_moments=zero7,
            bbox=(0, 0, 0, 0),
            params={"epsilon_frac": epsilon_frac, "n_points": int(len(pts))},
        )

    area = _polygon_area(pts)
    perimeter = _polygon_perimeter(pts)
    hull_area = _convex_hull_area(pts)
    solidity = float(area / hull_area) if hull_area > 0 else 0.0

    x_min, y_min = pts.min(axis=0)
    x_max, y_max = pts.max(axis=0)
    w = int(max(1, round(x_max - x_min)))
    h = int(max(1, round(y_max - y_min)))
    ar = float(max(w, h)) / float(max(min(w, h), 1))

    hu_log = _hu_moments(pts)

    return FragmentGeometry(
        area=area,
        perimeter=perimeter,
        aspect_ratio=ar,
        hull_area=hull_area,
        solidity=solidity,
        hu_moments=hu_log,
        bbox=(int(round(x_min)), int(round(y_min)), w, h),
        params={"epsilon_frac": epsilon_frac, "n_points": int(len(pts))},
    )


# --- similarity functions (ported verbatim from upstream) --------------------


def aspect_ratio_similarity(g1: FragmentGeometry, g2: FragmentGeometry) -> float:
    a1, a2 = g1.aspect_ratio, g2.aspect_ratio
    denom = max(a1, a2, 1e-9)
    return float(np.clip(1.0 - abs(a1 - a2) / denom, 0.0, 1.0))


def area_ratio_similarity(g1: FragmentGeometry, g2: FragmentGeometry) -> float:
    a1, a2 = g1.area, g2.area
    mx = max(a1, a2)
    if mx < 1e-9:
        return 1.0
    return float(np.clip(min(a1, a2) / mx, 0.0, 1.0))


def hu_moments_similarity(g1: FragmentGeometry, g2: FragmentGeometry) -> float:
    hu1 = g1.hu_moments
    hu2 = g2.hu_moments
    dist = float(np.linalg.norm(hu1 - hu2))
    return float(np.exp(-dist / 10.0))


def edge_length_similarity(len1: float, len2: float) -> float:
    mx = max(len1, len2)
    if mx < 1e-9:
        return 1.0
    return float(np.clip(min(len1, len2) / mx, 0.0, 1.0))


def match_geometry(
    g1: FragmentGeometry,
    g2: FragmentGeometry,
    w_aspect: float = 0.3,
    w_area: float = 0.4,
    w_hu: float = 0.3,
    edge_len1: Optional[float] = None,
    edge_len2: Optional[float] = None,
) -> GeometricMatchResult:
    total = w_aspect + w_area + w_hu
    if total < 1e-9:
        total = 1.0
    wa, wA, wh = w_aspect / total, w_area / total, w_hu / total

    s_aspect = aspect_ratio_similarity(g1, g2)
    s_area = area_ratio_similarity(g1, g2)
    s_hu = hu_moments_similarity(g1, g2)

    score = float(wa * s_aspect + wA * s_area + wh * s_hu)
    score = float(np.clip(score, 0.0, 1.0))

    params: Dict = {"w_aspect": w_aspect, "w_area": w_area, "w_hu": w_hu}
    if edge_len1 is not None and edge_len2 is not None:
        el_score = edge_length_similarity(edge_len1, edge_len2)
        score = float(np.clip((score + el_score) / 2.0, 0.0, 1.0))
        params["edge_len_score"] = el_score

    return GeometricMatchResult(
        score=score,
        aspect_score=s_aspect,
        area_score=s_area,
        hu_score=s_hu,
        method="geometric",
        params=params,
    )


def batch_geometry_match(
    geometries: List[FragmentGeometry],
    pairs: List[Tuple[int, int]],
    w_aspect: float = 0.3,
    w_area: float = 0.4,
    w_hu: float = 0.3,
) -> List[GeometricMatchResult]:
    return [
        match_geometry(
            geometries[i],
            geometries[j],
            w_aspect=w_aspect,
            w_area=w_area,
            w_hu=w_hu,
        )
        for i, j in pairs
    ]

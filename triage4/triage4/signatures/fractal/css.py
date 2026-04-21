"""Curvature Scale Space (CSS) shape descriptor.

Adapted from svend4/meta2 — ``puzzle_reconstruction/algorithms/fractal/css.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Use case in triage4:
- wound-boundary shape matching and comparison;
- posture-silhouette similarity between frames;
- anomalous-shape flags on thermal overlays.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
from scipy.ndimage import gaussian_filter1d


def curvature_scale_space(
    contour: np.ndarray,
    sigma_range: List[float] | None = None,
    n_sigmas: int = 7,
) -> List[Tuple[float, np.ndarray]]:
    """CSS-представление замкнутого контура."""
    if sigma_range is None:
        sigma_range = np.geomspace(1, 64, n_sigmas).tolist()

    x = np.asarray(contour[:, 0], dtype=float)
    y = np.asarray(contour[:, 1], dtype=float)
    t = _arc_length_param(x, y)

    css: list[tuple[float, np.ndarray]] = []
    for sigma in sigma_range:
        zc = _zero_crossings_at_sigma(x, y, t, float(sigma))
        css.append((float(sigma), zc))
    return css


def css_to_feature_vector(
    css: List[Tuple[float, np.ndarray]], n_bins: int = 64
) -> np.ndarray:
    """Плоский унифицированный вектор признаков из CSS-представления."""
    parts = []
    for _, zc in css:
        hist, _ = np.histogram(zc, bins=n_bins, range=(0.0, 1.0))
        parts.append(hist.astype(float))
    if not parts:
        return np.zeros(n_bins)
    vec = np.concatenate(parts)
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        return vec / norm
    return np.ones(len(vec)) / np.sqrt(len(vec)) if len(vec) > 0 else vec


def css_similarity(css_a: np.ndarray, css_b: np.ndarray) -> float:
    """Косинусное сходство двух CSS-векторов, [0, 1]."""
    a = np.asarray(css_a, dtype=float)
    b = np.asarray(css_b, dtype=float)
    if a.shape != b.shape:
        n = min(len(a), len(b))
        a = a[:n]
        b = b[:n]
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def css_similarity_mirror(css_a: np.ndarray, css_b: np.ndarray) -> float:
    """Сходство, устойчивое к зеркальному отражению контура."""
    direct = css_similarity(css_a, css_b)
    mirrored = css_similarity(css_a, css_b[::-1])
    return max(direct, mirrored)


def _arc_length_param(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    dx = np.diff(x, append=x[0])
    dy = np.diff(y, append=y[0])
    seg = np.hypot(dx, dy)
    cumlen = np.concatenate([[0], np.cumsum(seg[:-1])])
    total = float(cumlen[-1])
    if total == 0:
        return np.linspace(0, 1, len(x))
    return cumlen / total


def _zero_crossings_at_sigma(
    x: np.ndarray, y: np.ndarray, t: np.ndarray, sigma: float
) -> np.ndarray:
    Xs = gaussian_filter1d(x, sigma, mode="wrap")
    Ys = gaussian_filter1d(y, sigma, mode="wrap")
    Xs1 = np.gradient(Xs)
    Xs2 = np.gradient(Xs1)
    Ys1 = np.gradient(Ys)
    Ys2 = np.gradient(Ys1)

    denom = (Xs1 ** 2 + Ys1 ** 2) ** 1.5
    kappa = (Xs1 * Ys2 - Xs2 * Ys1) / (denom + 1e-10)

    sign_changes = np.where(np.diff(np.sign(kappa)))[0]

    zero_t: list[float] = []
    for idx in sign_changes:
        if abs(kappa[idx + 1] - kappa[idx]) < 1e-15:
            continue
        frac = -kappa[idx] / (kappa[idx + 1] - kappa[idx])
        nxt = min(idx + 1, len(t) - 1)
        t_zero = t[idx] + frac * (t[nxt] - t[idx])
        zero_t.append(float(t_zero))

    return np.array(zero_t) if zero_t else np.array([])

"""Triage-friendly facade over the boundary-matcher distances.

``boundary_matcher`` (ported verbatim from meta2) carries the 4-sides bbox
concept of torn-document fragments. For triage use (wound boundaries, body
silhouettes, posture shapes) we don't care about sides — we just want to
compare two ordered 2D point sequences directly.

This module exposes the three canonical shape distances and a composite
score without the rectangle-side plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from triage4.matching.boundary_matcher import (
    chamfer_distance,
    frechet_approx,
    hausdorff_distance,
    score_boundary_pair,
)


@dataclass
class ShapeMatch:
    hausdorff: float
    chamfer: float
    frechet: float
    total_score: float


def shape_distances(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    """Return raw (not-normalised) Hausdorff / Chamfer / Fréchet distances."""
    return {
        "hausdorff": hausdorff_distance(a, b),
        "chamfer": chamfer_distance(a, b),
        "frechet": frechet_approx(a, b),
    }


def shape_similarity(
    a: np.ndarray,
    b: np.ndarray,
    max_dist: float = 100.0,
    weights: tuple[float, float, float] | None = None,
) -> ShapeMatch:
    """Return a 0..1 shape-similarity score (1 = identical)."""
    h, c, f, total = score_boundary_pair(a, b, max_dist=max_dist, weights=weights)
    return ShapeMatch(hausdorff=h, chamfer=c, frechet=f, total_score=total)

"""Rank-list fusion algorithms.

Adapted from svend4/meta2 — ``puzzle_reconstruction/scoring/rank_fusion.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Triage use case: several independent scorers (bleeding, motion, perfusion,
posture, operator vote) each produce a ranked list of casualty ids. RRF and
Borda fuse them into a consensus ordering without needing compatible
score scales.

Adaptation notes:
- Copied verbatim; error strings translated to English.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np


def normalize_scores(scores: List[float], eps: float = 1e-9) -> List[float]:
    """Min-max normalize a list of scores into [0, 1]."""
    if not scores:
        raise ValueError("scores must not be empty")
    arr = np.asarray(scores, dtype=np.float64)
    mn, mx = arr.min(), arr.max()
    if mx - mn < eps:
        return [1.0] * len(scores)
    return list(((arr - mn) / (mx - mn)).tolist())


def reciprocal_rank_fusion(
    ranked_lists: List[List[int]], k: int = 60
) -> List[Tuple[int, float]]:
    """Reciprocal Rank Fusion.

    RRF(d) = Σ_r 1 / (k + rank_r(d)), with 1-based ranks.
    """
    if k <= 0:
        raise ValueError(f"k must be > 0, got {k}")
    if not ranked_lists:
        raise ValueError("ranked_lists must not be empty")

    scores: Dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def borda_count(ranked_lists: List[List[int]]) -> List[Tuple[int, float]]:
    """Borda count: position (N - rank - 1) points per list."""
    if not ranked_lists:
        raise ValueError("ranked_lists must not be empty")

    scores: Dict[int, float] = {}
    for ranked in ranked_lists:
        n = len(ranked)
        for rank, item_id in enumerate(ranked):
            points = float(n - rank - 1)
            scores[item_id] = scores.get(item_id, 0.0) + points

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def score_fusion(
    score_lists: List[List[Tuple[int, float]]],
    weights: Optional[List[float]] = None,
    normalize: bool = True,
) -> List[Tuple[int, float]]:
    """Weighted fusion of several (id, score) lists."""
    if not score_lists:
        raise ValueError("score_lists must not be empty")
    if weights is not None and len(weights) != len(score_lists):
        raise ValueError(
            f"weights ({len(weights)}) and score_lists ({len(score_lists)}) "
            f"must match in length"
        )
    if weights is None:
        weights = [1.0] * len(score_lists)

    total_w = sum(weights)
    if total_w < 1e-12:
        total_w = 1.0

    fused: Dict[int, float] = {}
    for sl, w in zip(score_lists, weights):
        if not sl:
            continue
        ids = [item_id for item_id, _ in sl]
        raw_scores = [s for _, s in sl]
        if normalize:
            raw_scores = normalize_scores(raw_scores)
        for item_id, sc in zip(ids, raw_scores):
            fused[item_id] = fused.get(item_id, 0.0) + w * sc / total_w

    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


def fuse_rankings(
    ranked_lists: List[List[int]], method: str = "rrf", k: int = 60
) -> List[Tuple[int, float]]:
    """Facade: pick RRF or Borda by name."""
    if method == "rrf":
        return reciprocal_rank_fusion(ranked_lists, k=k)
    if method == "borda":
        return borda_count(ranked_lists)
    raise ValueError(f"unknown method {method!r}, available: 'rrf', 'borda'")

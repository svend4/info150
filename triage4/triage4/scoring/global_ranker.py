"""Global ranking across multiple score sources.

Adapted from svend4/meta2 — ``puzzle_reconstruction/scoring/global_ranker.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Copied verbatim; error strings translated to English.
- Upstream aggregates boundary/SIFT/texture N×N similarity matrices into
  a single global ranking of fragment pairs. In triage4 the same
  primitives aggregate multiple signature matrices (motion, perfusion,
  bleeding, thermal) into a single casualty-pair ranking — useful when
  the operator wants one consensus list of similar casualties across
  all channels.
- ``RankedPair`` / ``rank_pairs`` re-exported under triage-friendly
  names (``GlobalRankedPair``, ``global_rank_pairs``) in the package
  init to avoid clashing with earlier rankers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class RankedPair:
    idx1: int
    idx2: int
    score: float
    rank: int
    component_scores: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.idx1 < 0:
            raise ValueError(f"idx1 must be >= 0, got {self.idx1}")
        if self.idx2 < 0:
            raise ValueError(f"idx2 must be >= 0, got {self.idx2}")
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be in [0, 1], got {self.score}")
        if self.rank < 0:
            raise ValueError(f"rank must be >= 0, got {self.rank}")

    @property
    def pair(self) -> Tuple[int, int]:
        return (self.idx1, self.idx2)


@dataclass
class RankingConfig:
    weights: Dict[str, float] = field(
        default_factory=lambda: {"boundary": 0.5, "sift": 0.3, "texture": 0.2}
    )
    top_k: int = 5
    normalize: bool = True
    min_score: float = 0.0
    symmetric: bool = True

    def __post_init__(self) -> None:
        for name, w in self.weights.items():
            if w < 0.0:
                raise ValueError(f"weight '{name}' must be >= 0, got {w}")
        if self.top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {self.top_k}")
        if self.min_score < 0.0:
            raise ValueError(f"min_score must be >= 0, got {self.min_score}")


def normalize_matrix(M: np.ndarray) -> np.ndarray:
    M = np.asarray(M, dtype=np.float64)
    if M.ndim != 2 or M.shape[0] != M.shape[1]:
        raise ValueError(f"M must be square 2-D, got shape={M.shape}")
    N = M.shape[0]
    mask = ~np.eye(N, dtype=bool)
    vals = M[mask]
    vmin = vals.min() if len(vals) else 0.0
    vmax = vals.max() if len(vals) else 0.0
    if vmax - vmin < 1e-12:
        result = np.zeros_like(M)
    else:
        result = (M - vmin) / (vmax - vmin)
    np.fill_diagonal(result, 0.0)
    return result


def aggregate_score_matrices(
    matrices: Dict[str, np.ndarray],
    weights: Optional[Dict[str, float]] = None,
    normalize: bool = True,
    symmetric: bool = True,
) -> np.ndarray:
    if not matrices:
        raise ValueError("matrices must not be empty")

    names = list(matrices.keys())
    mats = list(matrices.values())

    N = mats[0].shape[0]
    for m in mats[1:]:
        if m.shape != (N, N):
            raise ValueError(
                f"all matrices must share shape ({N}, {N}), got {m.shape}"
            )

    if weights is None:
        weights = {n: 1.0 for n in names}

    total_weight = sum(weights.get(n, 0.0) for n in names)
    if total_weight < 1e-12:
        total_weight = 1.0

    result = np.zeros((N, N), dtype=np.float64)
    for name, mat in zip(names, mats):
        w = weights.get(name, 0.0)
        if w == 0.0:
            continue
        m = mat.astype(np.float64)
        if normalize:
            m = normalize_matrix(m)
        result += w * m

    result /= total_weight
    np.fill_diagonal(result, 0.0)

    if symmetric:
        result = (result + result.T) / 2.0

    return result


def rank_pairs(
    agg_matrix: np.ndarray, min_score: float = 0.0
) -> List[RankedPair]:
    agg_matrix = np.asarray(agg_matrix, dtype=np.float64)
    if agg_matrix.ndim != 2 or agg_matrix.shape[0] != agg_matrix.shape[1]:
        raise ValueError("agg_matrix must be square 2-D")

    N = agg_matrix.shape[0]
    pairs: List[Tuple[float, int, int]] = []
    for i in range(N):
        for j in range(i + 1, N):
            score = float(agg_matrix[i, j])
            if score >= min_score:
                pairs.append((score, i, j))

    pairs.sort(key=lambda x: x[0], reverse=True)
    return [
        RankedPair(idx1=i, idx2=j, score=s, rank=r)
        for r, (s, i, j) in enumerate(pairs)
    ]


def top_k_candidates(
    ranked_pairs: List[RankedPair], n_fragments: int, k: int
) -> Dict[int, List[RankedPair]]:
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if n_fragments < 1:
        raise ValueError(f"n_fragments must be >= 1, got {n_fragments}")

    result: Dict[int, List[RankedPair]] = {i: [] for i in range(n_fragments)}
    for pair in ranked_pairs:
        for fid in (pair.idx1, pair.idx2):
            if fid < n_fragments and len(result[fid]) < k:
                result[fid].append(pair)
    return result


def global_rank(
    matrices: Dict[str, np.ndarray], cfg: Optional[RankingConfig] = None
) -> List[RankedPair]:
    if cfg is None:
        cfg = RankingConfig()
    agg = aggregate_score_matrices(
        matrices,
        weights=cfg.weights,
        normalize=cfg.normalize,
        symmetric=cfg.symmetric,
    )
    return rank_pairs(agg, min_score=cfg.min_score)


def score_vector(
    ranked_pairs: List[RankedPair], n_fragments: int
) -> np.ndarray:
    if n_fragments < 1:
        raise ValueError(f"n_fragments must be >= 1, got {n_fragments}")
    scores = np.zeros(n_fragments, dtype=np.float64)
    counts = np.zeros(n_fragments, dtype=np.int64)
    for pair in ranked_pairs:
        for fid in (pair.idx1, pair.idx2):
            if fid < n_fragments:
                scores[fid] += pair.score
                counts[fid] += 1
    mask = counts > 0
    scores[mask] /= counts[mask]
    return scores


def batch_global_rank(
    matrix_groups: List[Dict[str, np.ndarray]],
    cfg: Optional[RankingConfig] = None,
) -> List[List[RankedPair]]:
    return [global_rank(matrices, cfg) for matrices in matrix_groups]

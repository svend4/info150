"""Candidate pair ranking.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/candidate_ranker.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Upstream ranks fragment pairs for torn-document reassembly.
- triage4 reuses the same primitives to rank casualty-to-medic / robot-to-
  casualty / revisit candidates by fused score.
- The verbatim upstream API is preserved; only error strings were
  translated from Russian to English for consistency with the rest of the
  triage4 code base.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np


@dataclass
class CandidatePair:
    """Scored candidate pair of entity indices."""

    idx1: int
    idx2: int
    score: float
    meta: Dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"CandidatePair(({self.idx1},{self.idx2}), "
            f"score={self.score:.4f})"
        )

    def __lt__(self, other: "CandidatePair") -> bool:
        # Higher score first — `sorted` treats the "smaller" element as first.
        return self.score > other.score


def score_pair(idx1: int, idx2: int, score: float, **meta) -> CandidatePair:
    return CandidatePair(idx1=idx1, idx2=idx2, score=float(score), meta=dict(meta))


def rank_pairs(pairs: List[CandidatePair]) -> List[CandidatePair]:
    return sorted(pairs, key=lambda p: p.score, reverse=True)


def filter_by_score(
    pairs: List[CandidatePair], threshold: float = 0.5
) -> List[CandidatePair]:
    """Return ranked pairs with score strictly above ``threshold``."""
    return [p for p in rank_pairs(pairs) if p.score > threshold]


def deduplicate_pairs(pairs: List[CandidatePair]) -> List[CandidatePair]:
    """Greedy dedup: keep the highest-score pair for each unused index."""
    used: set[int] = set()
    result: List[CandidatePair] = []
    for p in rank_pairs(pairs):
        if p.idx1 not in used and p.idx2 not in used:
            result.append(p)
            used.add(p.idx1)
            used.add(p.idx2)
    return result


def top_k(
    pairs: List[CandidatePair], k: int, deduplicate: bool = False
) -> List[CandidatePair]:
    k = max(0, k)
    ranked = deduplicate_pairs(pairs) if deduplicate else rank_pairs(pairs)
    return ranked[:k]


def batch_rank(
    score_matrix: np.ndarray,
    threshold: float = 0.0,
    symmetric: bool = True,
) -> List[CandidatePair]:
    """Turn an N×N score matrix into a ranked list of CandidatePair."""
    mat = np.asarray(score_matrix, dtype=np.float32)
    if mat.ndim != 2:
        raise ValueError(f"score_matrix must be 2-D, got shape {mat.shape}")
    n, m = mat.shape
    if n != m:
        raise ValueError(f"score_matrix must be square (N×N), got {n}×{m}")

    pairs: List[CandidatePair] = []
    for i in range(n):
        j_start = i + 1 if symmetric else 0
        for j in range(j_start, n):
            if i == j:
                continue
            s = float(mat[i, j])
            if s > threshold:
                pairs.append(CandidatePair(idx1=i, idx2=j, score=s))

    return rank_pairs(pairs)

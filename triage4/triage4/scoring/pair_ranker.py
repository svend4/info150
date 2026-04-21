"""Structured ranking pipeline for scored pairs.

Adapted from svend4/meta2 — ``puzzle_reconstruction/scoring/pair_ranker.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Copied verbatim; error strings translated to English.
- This module defines ``rank_pairs`` — a more structured pipeline
  (RankConfig → RankedPair → RankResult) than the simpler
  ``candidate_ranker.rank_pairs``. Both are kept.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class RankConfig:
    top_k: int = 0
    ascending: bool = False
    deduplicate: bool = True
    min_score: float = 0.0
    score_field: str = "score"

    def __post_init__(self) -> None:
        if self.top_k < 0:
            raise ValueError(f"top_k must be >= 0, got {self.top_k}")
        if self.min_score < 0.0:
            raise ValueError(f"min_score must be >= 0, got {self.min_score}")
        if self.score_field not in ("score", "rank"):
            raise ValueError(
                f"score_field must be 'score' or 'rank', got {self.score_field!r}"
            )


@dataclass
class RankedPair:
    pair: Tuple[int, int]
    score: float
    rank: int
    scores: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.score < 0.0:
            raise ValueError(f"score must be >= 0, got {self.score}")
        if self.rank < 1:
            raise ValueError(f"rank must be >= 1, got {self.rank}")

    @property
    def fragment_a(self) -> int:
        return self.pair[0]

    @property
    def fragment_b(self) -> int:
        return self.pair[1]

    @property
    def n_metrics(self) -> int:
        return len(self.scores)


@dataclass
class RankResult:
    ranked: List[RankedPair]
    n_pairs: int
    n_ranked: int
    top_score: float
    mean_score: float

    def __post_init__(self) -> None:
        for name, val in (("n_pairs", self.n_pairs), ("n_ranked", self.n_ranked)):
            if val < 0:
                raise ValueError(f"{name} must be >= 0, got {val}")
        if self.top_score < 0.0:
            raise ValueError(f"top_score must be >= 0, got {self.top_score}")
        if self.mean_score < 0.0:
            raise ValueError(f"mean_score must be >= 0, got {self.mean_score}")

    @property
    def top_pair(self) -> Optional[Tuple[int, int]]:
        return self.ranked[0].pair if self.ranked else None

    @property
    def compression_ratio(self) -> float:
        if self.n_pairs == 0:
            return 0.0
        return float(self.n_ranked) / float(self.n_pairs)


def _normalize_pair(pair: Tuple[int, int]) -> Tuple[int, int]:
    a, b = pair
    return (min(a, b), max(a, b))


def compute_pair_score(
    metric_scores: Dict[str, float], weights: Optional[Dict[str, float]] = None
) -> float:
    if not metric_scores:
        raise ValueError("metric_scores must not be empty")
    for k, v in metric_scores.items():
        if v < 0.0:
            raise ValueError(f"score '{k}' must be >= 0, got {v}")

    if weights is None:
        weights = {k: 1.0 for k in metric_scores}

    w_sum = sum(weights.get(k, 1.0) for k in metric_scores) + 1e-12
    score = sum(
        metric_scores[k] * weights.get(k, 1.0) for k in metric_scores
    ) / w_sum
    return float(np.clip(score, 0.0, None))


def rank_pairs(
    pairs: List[Tuple[int, int]],
    scores: List[float],
    cfg: Optional[RankConfig] = None,
    metric_scores_list: Optional[List[Dict[str, float]]] = None,
) -> RankResult:
    if cfg is None:
        cfg = RankConfig()
    if len(pairs) != len(scores):
        raise ValueError(
            f"pairs ({len(pairs)}) and scores ({len(scores)}) must match in length"
        )

    norm_pairs = [_normalize_pair(p) if cfg.deduplicate else p for p in pairs]

    seen: dict = {}
    for i, (p, s) in enumerate(zip(norm_pairs, scores)):
        if p not in seen or s > seen[p][0]:
            seen[p] = (s, i)

    dedup_pairs = list(seen.keys())
    dedup_scores = [seen[p][0] for p in dedup_pairs]
    dedup_indices = [seen[p][1] for p in dedup_pairs]

    filtered = [
        (p, s, idx)
        for p, s, idx in zip(dedup_pairs, dedup_scores, dedup_indices)
        if s >= cfg.min_score
    ]

    n_pairs_total = len(pairs)

    if not filtered:
        return RankResult(
            ranked=[],
            n_pairs=n_pairs_total,
            n_ranked=0,
            top_score=0.0,
            mean_score=0.0,
        )

    filtered.sort(key=lambda x: x[1], reverse=not cfg.ascending)

    if cfg.top_k > 0:
        filtered = filtered[: cfg.top_k]

    ranked: List[RankedPair] = []
    for rank_idx, (p, s, orig_idx) in enumerate(filtered, start=1):
        ms = metric_scores_list[orig_idx] if metric_scores_list is not None else {}
        ranked.append(RankedPair(pair=p, score=s, rank=rank_idx, scores=ms))

    top_score = float(max(rp.score for rp in ranked))
    mean_score = float(np.mean([rp.score for rp in ranked]))

    return RankResult(
        ranked=ranked,
        n_pairs=n_pairs_total,
        n_ranked=len(ranked),
        top_score=top_score,
        mean_score=mean_score,
    )


def build_rank_matrix(result: RankResult, n_fragments: int) -> np.ndarray:
    if n_fragments < 1:
        raise ValueError(f"n_fragments must be >= 1, got {n_fragments}")
    matrix = np.zeros((n_fragments, n_fragments), dtype=int)
    for rp in result.ranked:
        a, b = rp.pair
        if 0 <= a < n_fragments and 0 <= b < n_fragments:
            matrix[a, b] = rp.rank
            matrix[b, a] = rp.rank
    return matrix


def merge_rank_results(
    results: List[RankResult], cfg: Optional[RankConfig] = None
) -> RankResult:
    if not results:
        raise ValueError("results must not be empty")

    all_pairs: List[Tuple[int, int]] = []
    all_scores: List[float] = []
    for r in results:
        for rp in r.ranked:
            all_pairs.append(rp.pair)
            all_scores.append(rp.score)

    return rank_pairs(all_pairs, all_scores, cfg)

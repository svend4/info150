"""Score fusion primitives.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/score_combiner.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Upstream uses ScoreVector/CombinedScore to fuse matcher scores for
  torn-document pairs. triage4 reuses the same structure to fuse
  signature scores (bleeding, motion, perfusion, …) for a single
  casualty into a weighted urgency score with explicit contributions.
- The ``idx1``/``idx2`` field pair is preserved for compatibility but
  typically holds ``(casualty_idx, 0)`` in triage usage (a single node,
  not a pair).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class ScoreVector:
    """Набор оценок от нескольких источников для одной сущности.

    In triage4:
      idx1 — casualty index (or any stable id hash); idx2 unused (kept 0).
      scores — {signature_name: 0..1} for one casualty snapshot.
    """

    idx1: int
    idx2: int
    scores: Dict[str, float]
    params: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.idx1 < 0:
            raise ValueError(f"idx1 must be >= 0, got {self.idx1}")
        if self.idx2 < 0:
            raise ValueError(f"idx2 must be >= 0, got {self.idx2}")
        for name, val in self.scores.items():
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"score '{name}' must be in [0, 1], got {val}")

    @property
    def pair(self) -> tuple[int, int]:
        return (self.idx1, self.idx2)

    def __len__(self) -> int:
        return len(self.scores)


@dataclass
class CombinedScore:
    """Итоговая комбинированная оценка."""

    idx1: int
    idx2: int
    score: float
    contributions: Dict[str, float] = field(default_factory=dict)
    params: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.idx1 < 0:
            raise ValueError(f"idx1 must be >= 0, got {self.idx1}")
        if self.idx2 < 0:
            raise ValueError(f"idx2 must be >= 0, got {self.idx2}")
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be in [0, 1], got {self.score}")

    @property
    def pair(self) -> tuple[int, int]:
        return (self.idx1, self.idx2)


def weighted_combine(
    sv: ScoreVector, weights: Optional[Dict[str, float]] = None
) -> CombinedScore:
    """Взвешенное среднее оценок из ScoreVector."""
    if not sv.scores:
        raise ValueError("ScoreVector.scores must not be empty")

    names = list(sv.scores.keys())

    if weights is None:
        w = {n: 1.0 for n in names}
    else:
        for n, val in weights.items():
            if val < 0.0:
                raise ValueError(f"weight '{n}' must be >= 0, got {val}")
        w = {n: weights.get(n, 1.0) for n in names}

    total_w = sum(w[n] for n in names)
    if total_w <= 0.0:
        raise ValueError("sum of weights must be > 0")

    combined = sum(sv.scores[n] * w[n] for n in names) / total_w
    combined = float(np.clip(combined, 0.0, 1.0))

    contributions = {n: sv.scores[n] * w[n] / total_w for n in names}
    return CombinedScore(
        idx1=sv.idx1, idx2=sv.idx2, score=combined, contributions=contributions
    )


def min_combine(sv: ScoreVector) -> CombinedScore:
    """Комбинирование минимумом."""
    if not sv.scores:
        raise ValueError("ScoreVector.scores must not be empty")
    score = float(min(sv.scores.values()))
    return CombinedScore(
        idx1=sv.idx1, idx2=sv.idx2, score=score, contributions=dict(sv.scores)
    )


def max_combine(sv: ScoreVector) -> CombinedScore:
    """Комбинирование максимумом."""
    if not sv.scores:
        raise ValueError("ScoreVector.scores must not be empty")
    score = float(max(sv.scores.values()))
    return CombinedScore(
        idx1=sv.idx1, idx2=sv.idx2, score=score, contributions=dict(sv.scores)
    )


def rank_combine(score_vectors: List[ScoreVector]) -> List[CombinedScore]:
    """Ранговое слияние: средний нормализованный ранг."""
    if not score_vectors:
        return []

    n = len(score_vectors)
    matcher_names = list(score_vectors[0].scores.keys())

    for sv in score_vectors:
        if set(sv.scores.keys()) != set(matcher_names):
            raise ValueError("all ScoreVector must share the same matcher keys")

    rank_sums = np.zeros(n, dtype=np.float64)
    for name in matcher_names:
        values = np.array([sv.scores[name] for sv in score_vectors], dtype=np.float64)
        order = np.argsort(-values)
        ranks = np.empty(n, dtype=np.float64)
        ranks[order] = np.arange(n, dtype=np.float64)
        rank_sums += ranks

    if n == 1:
        norm_scores = np.ones(n, dtype=np.float64)
    else:
        avg_ranks = rank_sums / len(matcher_names)
        norm_scores = 1.0 - avg_ranks / (n - 1)
        norm_scores = np.clip(norm_scores, 0.0, 1.0)

    results: list[CombinedScore] = []
    for i, sv in enumerate(score_vectors):
        results.append(
            CombinedScore(
                idx1=sv.idx1,
                idx2=sv.idx2,
                score=float(norm_scores[i]),
                contributions=dict(sv.scores),
            )
        )
    return results


def normalize_score_vectors(score_vectors: List[ScoreVector]) -> List[ScoreVector]:
    """Min-max нормализация оценок каждого источника по всем сущностям."""
    if not score_vectors:
        return []

    matcher_names = list(score_vectors[0].scores.keys())
    all_scores: Dict[str, List[float]] = {n: [] for n in matcher_names}
    for sv in score_vectors:
        for n in matcher_names:
            all_scores[n].append(sv.scores.get(n, 0.0))

    mins = {n: min(v) for n, v in all_scores.items()}
    maxs = {n: max(v) for n, v in all_scores.items()}

    result: list[ScoreVector] = []
    for sv in score_vectors:
        new_scores: Dict[str, float] = {}
        for n in matcher_names:
            mn, mx = mins[n], maxs[n]
            if mx - mn < 1e-12:
                new_scores[n] = 0.0
            else:
                new_scores[n] = (sv.scores[n] - mn) / (mx - mn)
        result.append(
            ScoreVector(
                idx1=sv.idx1, idx2=sv.idx2, scores=new_scores, params=dict(sv.params)
            )
        )
    return result


def batch_combine(
    score_vectors: List[ScoreVector],
    method: str = "weighted",
    weights: Optional[Dict[str, float]] = None,
) -> List[CombinedScore]:
    """Пакетное комбинирование списка ScoreVector, сортировка по score desc."""
    valid = {"weighted", "min", "max", "rank"}
    if method not in valid:
        raise ValueError(f"unknown method '{method}', valid: {sorted(valid)}")
    if not score_vectors:
        return []

    if method == "rank":
        results = rank_combine(score_vectors)
    else:
        dispatch = {
            "weighted": lambda sv: weighted_combine(sv, weights),
            "min": min_combine,
            "max": max_combine,
        }
        results = [dispatch[method](sv) for sv in score_vectors]

    results.sort(key=lambda cs: cs.score, reverse=True)
    return results

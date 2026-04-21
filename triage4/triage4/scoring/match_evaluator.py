"""Match-quality evaluation metrics (precision / recall / F-beta).

Adapted from svend4/meta2 — ``puzzle_reconstruction/scoring/match_evaluator.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Copied verbatim; error strings translated to English.
- Triage use case: evaluate triage decisions against ground truth
  (post-mission outcomes or synthetic labels) with standard precision /
  recall / F1 metrics; compute mean F1 across a batch of casualties.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class EvalConfig:
    min_score: float = 0.0
    max_score: float = 1.0
    n_levels: int = 10
    beta: float = 1.0

    def __post_init__(self) -> None:
        if self.min_score < 0.0:
            raise ValueError(f"min_score must be >= 0, got {self.min_score}")
        if self.max_score <= self.min_score:
            raise ValueError(
                f"max_score must be > min_score: "
                f"{self.max_score} <= {self.min_score}"
            )
        if self.n_levels < 2:
            raise ValueError(f"n_levels must be >= 2, got {self.n_levels}")
        if self.beta <= 0.0:
            raise ValueError(f"beta must be > 0, got {self.beta}")


@dataclass
class MatchEval:
    pair: Tuple[int, int]
    score: float
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def __post_init__(self) -> None:
        if self.score < 0.0:
            raise ValueError(f"score must be >= 0, got {self.score}")
        for name, val in (("tp", self.tp), ("fp", self.fp), ("fn", self.fn)):
            if val < 0:
                raise ValueError(f"{name} must be >= 0, got {val}")

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return float(self.tp) / float(denom) if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return float(self.tp) / float(denom) if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2.0 * p * r / (p + r) if (p + r) > 0.0 else 0.0


@dataclass
class EvalReport:
    evals: List[MatchEval]
    n_pairs: int
    mean_score: float
    mean_f1: float

    def __post_init__(self) -> None:
        if self.n_pairs < 0:
            raise ValueError(f"n_pairs must be >= 0, got {self.n_pairs}")
        if self.mean_score < 0.0:
            raise ValueError(f"mean_score must be >= 0, got {self.mean_score}")
        if self.mean_f1 < 0.0:
            raise ValueError(f"mean_f1 must be >= 0, got {self.mean_f1}")

    @property
    def best_f1(self) -> float:
        if not self.evals:
            return 0.0
        return max(e.f1 for e in self.evals)

    @property
    def best_pair(self) -> Optional[Tuple[int, int]]:
        if not self.evals:
            return None
        return max(self.evals, key=lambda e: e.f1).pair


def compute_precision(tp: int, fp: int) -> float:
    if tp < 0:
        raise ValueError(f"tp must be >= 0, got {tp}")
    if fp < 0:
        raise ValueError(f"fp must be >= 0, got {fp}")
    denom = tp + fp
    return float(tp) / float(denom) if denom > 0 else 0.0


def compute_recall(tp: int, fn: int) -> float:
    if tp < 0:
        raise ValueError(f"tp must be >= 0, got {tp}")
    if fn < 0:
        raise ValueError(f"fn must be >= 0, got {fn}")
    denom = tp + fn
    return float(tp) / float(denom) if denom > 0 else 0.0


def compute_f_score(precision: float, recall: float, beta: float = 1.0) -> float:
    if beta <= 0.0:
        raise ValueError(f"beta must be > 0, got {beta}")
    b2 = beta ** 2
    denom = b2 * precision + recall
    if denom < 1e-12:
        return 0.0
    return float((1.0 + b2) * precision * recall / denom)


def evaluate_match(
    pair: Tuple[int, int], score: float, tp: int, fp: int, fn: int
) -> MatchEval:
    return MatchEval(pair=pair, score=score, tp=tp, fp=fp, fn=fn)


def evaluate_batch_matches(
    pairs: List[Tuple[int, int]],
    scores: List[float],
    tp_list: List[int],
    fp_list: List[int],
    fn_list: List[int],
) -> List[MatchEval]:
    n = len(pairs)
    for name, lst in (
        ("scores", scores),
        ("tp_list", tp_list),
        ("fp_list", fp_list),
        ("fn_list", fn_list),
    ):
        if len(lst) != n:
            raise ValueError(f"length of {name} ({len(lst)}) != len(pairs) ({n})")
    return [
        evaluate_match(p, s, tp, fp, fn)
        for p, s, tp, fp, fn in zip(pairs, scores, tp_list, fp_list, fn_list)
    ]


def aggregate_eval(evals: List[MatchEval]) -> EvalReport:
    n = len(evals)
    if n == 0:
        return EvalReport(evals=[], n_pairs=0, mean_score=0.0, mean_f1=0.0)

    mean_score = float(np.mean([e.score for e in evals]))
    mean_f1 = float(np.mean([e.f1 for e in evals]))
    return EvalReport(
        evals=evals, n_pairs=n, mean_score=mean_score, mean_f1=mean_f1
    )


def filter_by_score(evals: List[MatchEval], threshold: float) -> List[MatchEval]:
    if threshold < 0.0:
        raise ValueError(f"threshold must be >= 0, got {threshold}")
    return [e for e in evals if e.score >= threshold]


def rank_matches(evals: List[MatchEval], by: str = "f1") -> List[MatchEval]:
    if by not in ("f1", "score"):
        raise ValueError(f"by must be 'f1' or 'score', got {by!r}")
    key = (lambda e: e.f1) if by == "f1" else (lambda e: e.score)
    return sorted(evals, key=key, reverse=True)

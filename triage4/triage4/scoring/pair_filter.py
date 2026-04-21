"""Multi-stage candidate-pair filtering.

Adapted from svend4/meta2 — ``puzzle_reconstruction/scoring/pair_filter.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Copied verbatim with error strings translated to English.
- This module's ``CandidatePair`` carries ``n_inliers`` / ``rank`` fields
  and is distinct from :class:`triage4.matching.candidate_ranker.CandidatePair`.
  To avoid a name clash at the package level, the dataclass is re-exported
  from :mod:`triage4.scoring` as ``FilterCandidatePair``.
- Same applies to ``deduplicate_pairs`` / ``filter_by_score``: exposed with
  ``filter_*`` prefixes at the package level.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


_FILTER_METHODS = {"score", "inlier", "rank", "combined"}


@dataclass
class FilterConfig:
    method: str = "combined"
    min_score: float = 0.0
    min_inliers: int = 0
    max_pairs: int = 100
    top_k_per_id: int = 5

    def __post_init__(self) -> None:
        if self.method not in _FILTER_METHODS:
            raise ValueError(
                f"method must be one of {_FILTER_METHODS}, got {self.method!r}"
            )
        if self.min_score < 0.0:
            raise ValueError(f"min_score must be >= 0, got {self.min_score}")
        if self.min_inliers < 0:
            raise ValueError(f"min_inliers must be >= 0, got {self.min_inliers}")
        if self.max_pairs < 1:
            raise ValueError(f"max_pairs must be >= 1, got {self.max_pairs}")
        if self.top_k_per_id < 1:
            raise ValueError(f"top_k_per_id must be >= 1, got {self.top_k_per_id}")


@dataclass
class CandidatePair:
    id_a: int
    id_b: int
    score: float
    n_inliers: int = 0
    rank: int = 0

    def __post_init__(self) -> None:
        if self.id_a < 0:
            raise ValueError(f"id_a must be >= 0, got {self.id_a}")
        if self.id_b < 0:
            raise ValueError(f"id_b must be >= 0, got {self.id_b}")
        if self.score < 0.0:
            raise ValueError(f"score must be >= 0, got {self.score}")
        if self.n_inliers < 0:
            raise ValueError(f"n_inliers must be >= 0, got {self.n_inliers}")
        if self.rank < 0:
            raise ValueError(f"rank must be >= 0, got {self.rank}")

    @property
    def pair(self) -> Tuple[int, int]:
        return (min(self.id_a, self.id_b), max(self.id_a, self.id_b))


@dataclass
class FilterReport:
    n_input: int = 0
    n_output: int = 0
    n_rejected: int = 0
    method: str = "combined"

    def __post_init__(self) -> None:
        if self.n_input < 0:
            raise ValueError(f"n_input must be >= 0, got {self.n_input}")
        if self.n_output < 0:
            raise ValueError(f"n_output must be >= 0, got {self.n_output}")
        if self.n_rejected < 0:
            raise ValueError(f"n_rejected must be >= 0, got {self.n_rejected}")

    @property
    def rejection_rate(self) -> float:
        if self.n_input == 0:
            return 0.0
        return float(self.n_rejected) / float(self.n_input)


def filter_by_score(
    pairs: List[CandidatePair], min_score: float = 0.0
) -> List[CandidatePair]:
    if min_score < 0.0:
        raise ValueError(f"min_score must be >= 0, got {min_score}")
    return [p for p in pairs if p.score >= min_score]


def filter_by_inlier_count(
    pairs: List[CandidatePair], min_inliers: int = 0
) -> List[CandidatePair]:
    if min_inliers < 0:
        raise ValueError(f"min_inliers must be >= 0, got {min_inliers}")
    return [p for p in pairs if p.n_inliers >= min_inliers]


def filter_top_k(pairs: List[CandidatePair], k: int) -> List[CandidatePair]:
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    return sorted(pairs, key=lambda p: p.score, reverse=True)[:k]


def deduplicate_pairs(pairs: List[CandidatePair]) -> List[CandidatePair]:
    best: Dict[Tuple[int, int], CandidatePair] = {}
    for p in pairs:
        key = p.pair
        if key not in best or p.score > best[key].score:
            best[key] = p
    return list(best.values())


def filter_top_k_per_fragment(
    pairs: List[CandidatePair], k: int = 5
) -> List[CandidatePair]:
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    sorted_pairs = sorted(pairs, key=lambda x: x.score, reverse=True)
    counts: Dict[int, int] = defaultdict(int)
    result: List[CandidatePair] = []
    for p in sorted_pairs:
        if counts[p.id_a] < k and counts[p.id_b] < k:
            result.append(p)
            counts[p.id_a] += 1
            counts[p.id_b] += 1
    return result


def filter_pairs(
    pairs: List[CandidatePair], cfg: Optional[FilterConfig] = None
) -> Tuple[List[CandidatePair], FilterReport]:
    if cfg is None:
        cfg = FilterConfig()

    n_input = len(pairs)
    result = list(pairs)

    if cfg.method in ("score", "combined"):
        result = filter_by_score(result, cfg.min_score)
    if cfg.method in ("inlier", "combined"):
        result = filter_by_inlier_count(result, cfg.min_inliers)

    result = deduplicate_pairs(result)

    if len(result) > cfg.top_k_per_id:
        result = filter_top_k_per_fragment(result, cfg.top_k_per_id)

    result = filter_top_k(result, cfg.max_pairs)

    report = FilterReport(
        n_input=n_input,
        n_output=len(result),
        n_rejected=n_input - len(result),
        method=cfg.method,
    )
    return result, report


def merge_filter_results(
    results: List[List[CandidatePair]],
) -> List[CandidatePair]:
    all_pairs: List[CandidatePair] = []
    for r in results:
        all_pairs.extend(r)
    return deduplicate_pairs(all_pairs)


def batch_filter(
    pair_lists: List[List[CandidatePair]],
    cfg: Optional[FilterConfig] = None,
) -> List[Tuple[List[CandidatePair], FilterReport]]:
    return [filter_pairs(pl, cfg) for pl in pair_lists]

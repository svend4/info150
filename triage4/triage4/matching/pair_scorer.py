"""Channel-weighted pair scoring.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/pair_scorer.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Upstream aggregates color/texture/geometry/gradient channels into a
  per-pair compatibility score for torn-document reassembly.
- triage4 uses the same primitives to aggregate independent casualty
  similarity channels (shape / signature / location / handoff history)
  with named channel weights.
- Error strings translated to English.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class ScoringWeights:
    color: float = 1.0
    texture: float = 1.0
    geometry: float = 1.0
    gradient: float = 1.0

    def __post_init__(self) -> None:
        for name in ("color", "texture", "geometry", "gradient"):
            val = getattr(self, name)
            if val < 0.0:
                raise ValueError(f"weight '{name}' must be >= 0, got {val}")
        if self.total == 0.0:
            raise ValueError("sum of weights must be > 0")

    @property
    def total(self) -> float:
        return self.color + self.texture + self.geometry + self.gradient

    def as_dict(self) -> Dict[str, float]:
        return {
            "color": self.color,
            "texture": self.texture,
            "geometry": self.geometry,
            "gradient": self.gradient,
        }

    def normalized(self) -> "ScoringWeights":
        t = self.total
        return ScoringWeights(
            color=self.color / t,
            texture=self.texture / t,
            geometry=self.geometry / t,
            gradient=self.gradient / t,
        )


@dataclass
class PairScoreResult:
    idx_a: int
    idx_b: int
    score: float
    channels: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be in [0, 1], got {self.score}")

    @property
    def n_channels(self) -> int:
        return len(self.channels)

    @property
    def pair_key(self) -> Tuple[int, int]:
        return (min(self.idx_a, self.idx_b), max(self.idx_a, self.idx_b))

    @property
    def dominant_channel(self) -> Optional[str]:
        if not self.channels:
            return None
        return max(self.channels, key=lambda k: self.channels[k])

    @property
    def is_strong_match(self) -> bool:
        return self.score >= 0.7


def aggregate_channels(
    channel_scores: Dict[str, float],
    weights: Optional[ScoringWeights] = None,
) -> float:
    """Weighted average of a {channel: score} dict."""
    if not channel_scores:
        raise ValueError("channel_scores must not be empty")
    for ch, v in channel_scores.items():
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"channel '{ch}' score must be in [0, 1], got {v}")

    if weights is None:
        weights = ScoringWeights()

    w_dict = weights.as_dict()
    w_sum = sum(w_dict.get(ch, 1.0) for ch in channel_scores) + 1e-12
    score = sum(
        channel_scores[ch] * w_dict.get(ch, 1.0) for ch in channel_scores
    ) / w_sum
    return float(np.clip(score, 0.0, 1.0))


def score_pair(
    idx_a: int,
    idx_b: int,
    channel_scores: Dict[str, float],
    weights: Optional[ScoringWeights] = None,
) -> PairScoreResult:
    agg = aggregate_channels(channel_scores, weights)
    return PairScoreResult(
        idx_a=idx_a, idx_b=idx_b, score=agg, channels=dict(channel_scores)
    )


def select_top_pairs(
    results: List[PairScoreResult],
    threshold: float = 0.0,
    top_k: int = 0,
) -> List[PairScoreResult]:
    if threshold < 0.0:
        raise ValueError(f"threshold must be >= 0, got {threshold}")
    if top_k < 0:
        raise ValueError(f"top_k must be >= 0, got {top_k}")

    filtered = [r for r in results if r.score >= threshold]
    filtered.sort(key=lambda r: r.score, reverse=True)
    if top_k > 0:
        filtered = filtered[:top_k]
    return filtered


def build_score_matrix(
    results: List[PairScoreResult], n_fragments: int
) -> np.ndarray:
    if n_fragments < 1:
        raise ValueError(f"n_fragments must be >= 1, got {n_fragments}")
    mat = np.zeros((n_fragments, n_fragments), dtype=np.float32)
    for r in results:
        a, b = r.idx_a, r.idx_b
        if 0 <= a < n_fragments and 0 <= b < n_fragments:
            mat[a, b] = r.score
            mat[b, a] = r.score
    return mat


def batch_score_pairs(
    pairs: List[Tuple[int, int]],
    channel_scores_list: List[Dict[str, float]],
    weights: Optional[ScoringWeights] = None,
) -> List[PairScoreResult]:
    if len(pairs) != len(channel_scores_list):
        raise ValueError(
            f"pairs ({len(pairs)}) and channel_scores_list "
            f"({len(channel_scores_list)}) must match in length"
        )
    return [
        score_pair(a, b, cs, weights)
        for (a, b), cs in zip(pairs, channel_scores_list)
    ]

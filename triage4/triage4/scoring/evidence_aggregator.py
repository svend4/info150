"""Evidence aggregation with channel weights, thresholds, and confidence.

Adapted from svend4/meta2 — ``puzzle_reconstruction/scoring/evidence_aggregator.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Triage use case:
- Aggregates heterogeneous evidence channels (bleeding score, motion
  score, perfusion, posture, thermal, operator vote) into a single
  confidence number per casualty with per-channel auditing.
- Supports per-channel thresholds so weak evidence is zeroed before
  fusion, and a ``require_all`` mode to reject partial observations.

Adaptation notes:
- Copied verbatim; error strings translated to English. ``pair_id`` field
  names are kept for compatibility with upstream; in triage4 it typically
  holds ``(casualty_idx, 0)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class EvidenceConfig:
    weights: Dict[str, float] = field(default_factory=dict)
    min_threshold: float = 0.0
    require_all: bool = False
    confidence_threshold: float = 0.5

    def __post_init__(self) -> None:
        if not (0.0 <= self.min_threshold <= 1.0):
            raise ValueError(
                f"min_threshold must be in [0, 1], got {self.min_threshold}"
            )
        if not (0.0 <= self.confidence_threshold <= 1.0):
            raise ValueError(
                f"confidence_threshold must be in [0, 1], "
                f"got {self.confidence_threshold}"
            )
        for ch, w in self.weights.items():
            if w < 0.0:
                raise ValueError(f"weight '{ch}' must be >= 0, got {w}")


@dataclass
class EvidenceScore:
    pair_id: Tuple[int, int]
    confidence: float
    channel_scores: Dict[str, float] = field(default_factory=dict)
    weighted_scores: Dict[str, float] = field(default_factory=dict)
    n_channels: int = 0

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )
        if self.n_channels < 0:
            raise ValueError(f"n_channels must be >= 0, got {self.n_channels}")
        a, b = self.pair_id
        if a < 0 or b < 0:
            raise ValueError(
                f"pair_id must be non-negative, got {self.pair_id}"
            )

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.5

    @property
    def dominant_channel(self) -> Optional[str]:
        if not self.weighted_scores:
            return None
        return max(self.weighted_scores, key=lambda k: self.weighted_scores[k])

    def summary(self) -> str:
        return (
            f"EvidenceScore(pair={self.pair_id}, confidence={self.confidence:.3f}, "
            f"channels={self.n_channels})"
        )


def weight_evidence(
    scores: Dict[str, float], weights: Dict[str, float]
) -> Dict[str, float]:
    for ch, s in scores.items():
        if not (0.0 <= s <= 1.0):
            raise ValueError(f"channel '{ch}' score must be in [0, 1], got {s}")
    for ch, w in weights.items():
        if w < 0.0:
            raise ValueError(f"weight '{ch}' must be >= 0, got {w}")
    return {ch: s * weights.get(ch, 1.0) for ch, s in scores.items()}


def threshold_evidence(
    scores: Dict[str, float], min_threshold: float
) -> Dict[str, float]:
    if not (0.0 <= min_threshold <= 1.0):
        raise ValueError(f"min_threshold must be in [0, 1], got {min_threshold}")
    return {ch: (s if s >= min_threshold else 0.0) for ch, s in scores.items()}


def compute_confidence(
    weighted_scores: Dict[str, float], weights: Dict[str, float]
) -> float:
    if not weighted_scores:
        return 0.0
    total_weight = sum(weights.get(ch, 1.0) for ch in weighted_scores)
    if total_weight == 0.0:
        return 0.0
    total = sum(weighted_scores.values())
    raw = total / total_weight
    return float(min(1.0, max(0.0, raw)))


def aggregate_evidence(
    scores: Dict[str, float],
    pair_id: Tuple[int, int] = (0, 0),
    cfg: Optional[EvidenceConfig] = None,
) -> EvidenceScore:
    if cfg is None:
        cfg = EvidenceConfig()

    thresholded = threshold_evidence(scores, cfg.min_threshold)

    if cfg.require_all and cfg.weights:
        missing = [
            ch
            for ch in cfg.weights
            if ch not in thresholded or thresholded[ch] == 0.0
        ]
        if missing:
            raise ValueError(
                f"require_all=True: missing channels {missing}"
            )

    weighted = weight_evidence(thresholded, cfg.weights)
    confidence = compute_confidence(weighted, cfg.weights)

    return EvidenceScore(
        pair_id=pair_id,
        confidence=confidence,
        channel_scores=dict(thresholded),
        weighted_scores=dict(weighted),
        n_channels=len(weighted),
    )


def rank_by_evidence(
    evidence_scores: List[EvidenceScore],
) -> List[EvidenceScore]:
    return sorted(evidence_scores, key=lambda e: e.confidence, reverse=True)


def batch_aggregate(
    batch: List[Dict[str, float]],
    pair_ids: Optional[List[Tuple[int, int]]] = None,
    cfg: Optional[EvidenceConfig] = None,
) -> List[EvidenceScore]:
    if pair_ids is not None and len(pair_ids) != len(batch):
        raise ValueError(
            f"pair_ids length ({len(pair_ids)}) != batch length ({len(batch)})"
        )
    results: List[EvidenceScore] = []
    for i, scores in enumerate(batch):
        pid = pair_ids[i] if pair_ids is not None else (i, i + 1)
        results.append(aggregate_evidence(scores, pair_id=pid, cfg=cfg))
    return results

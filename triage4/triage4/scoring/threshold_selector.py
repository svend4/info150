"""Threshold selection strategies.

Adapted from svend4/meta2 — ``puzzle_reconstruction/scoring/threshold_selector.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Triage use case:
- auto-calibrate the cut-off that separates "immediate" from "delayed"
  casualties when the dataset's score distribution shifts;
- pick an F-beta optimum when labelled outcomes are available (e.g.
  post-mission truth data);
- use Otsu / adaptive when there is no ground truth.

Adaptation notes:
- Copied verbatim; error strings translated to English.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np


_VALID_METHODS = {"fixed", "percentile", "otsu", "f1", "adaptive"}


@dataclass
class ThresholdConfig:
    method: str = "percentile"
    fixed_value: float = 0.5
    percentile: float = 50.0
    n_bins: int = 256
    beta: float = 1.0

    def __post_init__(self) -> None:
        if self.method not in _VALID_METHODS:
            raise ValueError(
                f"method must be one of {_VALID_METHODS}, got {self.method!r}"
            )
        if self.fixed_value < 0.0:
            raise ValueError(f"fixed_value must be >= 0, got {self.fixed_value}")
        if not (0.0 <= self.percentile <= 100.0):
            raise ValueError(
                f"percentile must be in [0, 100], got {self.percentile}"
            )
        if self.n_bins < 2:
            raise ValueError(f"n_bins must be >= 2, got {self.n_bins}")
        if self.beta <= 0.0:
            raise ValueError(f"beta must be > 0, got {self.beta}")


@dataclass
class ThresholdResult:
    threshold: float
    method: str
    n_above: int
    n_below: int
    n_total: int

    def __post_init__(self) -> None:
        if self.threshold < 0.0:
            raise ValueError(f"threshold must be >= 0, got {self.threshold}")
        for name, val in (
            ("n_above", self.n_above),
            ("n_below", self.n_below),
            ("n_total", self.n_total),
        ):
            if val < 0:
                raise ValueError(f"{name} must be >= 0, got {val}")

    @property
    def acceptance_ratio(self) -> float:
        if self.n_total == 0:
            return 0.0
        return float(self.n_above) / float(self.n_total)

    @property
    def rejection_ratio(self) -> float:
        if self.n_total == 0:
            return 0.0
        return float(self.n_below) / float(self.n_total)


def _make_result(scores: np.ndarray, threshold: float, method: str) -> ThresholdResult:
    n_above = int(np.sum(scores >= threshold))
    n_below = int(np.sum(scores < threshold))
    return ThresholdResult(
        threshold=float(threshold),
        method=method,
        n_above=n_above,
        n_below=n_below,
        n_total=len(scores),
    )


def select_fixed_threshold(
    scores: np.ndarray, value: float = 0.5
) -> ThresholdResult:
    s = np.asarray(scores, dtype=float).ravel()
    if len(s) == 0:
        raise ValueError("scores must not be empty")
    if value < 0.0:
        raise ValueError(f"value must be >= 0, got {value}")
    return _make_result(s, value, "fixed")


def select_percentile_threshold(
    scores: np.ndarray, percentile: float = 50.0
) -> ThresholdResult:
    s = np.asarray(scores, dtype=float).ravel()
    if len(s) == 0:
        raise ValueError("scores must not be empty")
    if not (0.0 <= percentile <= 100.0):
        raise ValueError(f"percentile must be in [0, 100], got {percentile}")
    threshold = float(np.percentile(s, percentile))
    return _make_result(s, threshold, "percentile")


def select_otsu_threshold(
    scores: np.ndarray, n_bins: int = 256
) -> ThresholdResult:
    s = np.asarray(scores, dtype=float).ravel()
    if len(s) == 0:
        raise ValueError("scores must not be empty")
    if n_bins < 2:
        raise ValueError(f"n_bins must be >= 2, got {n_bins}")

    s_min, s_max = s.min(), s.max()
    if s_min == s_max:
        return _make_result(s, float(s_min), "otsu")

    edges = np.linspace(s_min, s_max, n_bins + 1)
    hist, _ = np.histogram(s, bins=edges)
    hist = hist.astype(float)
    total = hist.sum()
    if total == 0:
        return _make_result(s, float(s_min), "otsu")

    bin_centers = 0.5 * (edges[:-1] + edges[1:])
    w_cumsum = np.cumsum(hist) / total
    mu_cumsum = np.cumsum(hist * bin_centers) / total

    mu_total = mu_cumsum[-1]
    w1 = w_cumsum[:-1]
    w2 = 1.0 - w1
    mu1 = np.divide(mu_cumsum[:-1], w1, out=np.zeros_like(w1), where=w1 > 0)
    mu2 = np.divide(
        (mu_total - mu_cumsum[:-1]),
        w2,
        out=np.zeros_like(w2),
        where=w2 > 0,
    )

    sigma_b2 = w1 * w2 * (mu1 - mu2) ** 2
    max_val = sigma_b2.max()
    plateau = np.where(sigma_b2 >= max_val * (1 - 1e-10))[0]
    best_idx = int(plateau[len(plateau) // 2])
    threshold = float(edges[best_idx + 1])
    return _make_result(s, threshold, "otsu")


def select_f1_threshold(
    scores: np.ndarray,
    labels: np.ndarray,
    n_candidates: int = 50,
    beta: float = 1.0,
) -> ThresholdResult:
    s = np.asarray(scores, dtype=float).ravel()
    y = np.asarray(labels, dtype=int).ravel()
    if len(s) == 0:
        raise ValueError("scores must not be empty")
    if len(s) != len(y):
        raise ValueError(
            f"scores ({len(s)}) and labels ({len(y)}) must match in length"
        )
    if beta <= 0.0:
        raise ValueError(f"beta must be > 0, got {beta}")
    if n_candidates < 2:
        raise ValueError(f"n_candidates must be >= 2, got {n_candidates}")

    candidates = np.linspace(s.min(), s.max(), n_candidates)
    best_thresh = candidates[0]
    best_fb = -1.0
    b2 = beta ** 2

    for t in candidates:
        pred = (s >= t).astype(int)
        tp = int(np.sum((pred == 1) & (y == 1)))
        fp = int(np.sum((pred == 1) & (y == 0)))
        fn = int(np.sum((pred == 0) & (y == 1)))
        denom = (1.0 + b2) * tp + b2 * fn + fp
        fb = (1.0 + b2) * tp / denom if denom > 0 else 0.0
        if fb > best_fb:
            best_fb = fb
            best_thresh = t

    return _make_result(s, float(best_thresh), "f1")


def select_adaptive_threshold(
    scores: np.ndarray, n_bins: int = 256
) -> ThresholdResult:
    s = np.asarray(scores, dtype=float).ravel()
    if len(s) == 0:
        raise ValueError("scores must not be empty")
    t_pct = select_percentile_threshold(s, 50.0).threshold
    t_otsu = select_otsu_threshold(s, n_bins).threshold
    threshold = (t_pct + t_otsu) / 2.0
    return _make_result(s, threshold, "adaptive")


def select_threshold(
    scores: np.ndarray,
    cfg: Optional[ThresholdConfig] = None,
    labels: Optional[np.ndarray] = None,
) -> ThresholdResult:
    if cfg is None:
        cfg = ThresholdConfig()

    s = np.asarray(scores, dtype=float).ravel()

    if cfg.method == "fixed":
        return select_fixed_threshold(s, cfg.fixed_value)
    if cfg.method == "percentile":
        return select_percentile_threshold(s, cfg.percentile)
    if cfg.method == "otsu":
        return select_otsu_threshold(s, cfg.n_bins)
    if cfg.method == "f1":
        if labels is None:
            raise ValueError("labels are required when method='f1'")
        return select_f1_threshold(s, labels, beta=cfg.beta)
    return select_adaptive_threshold(s, cfg.n_bins)


def apply_threshold(scores: np.ndarray, result: ThresholdResult) -> np.ndarray:
    return np.asarray(scores, dtype=float).ravel() >= result.threshold


def batch_select_thresholds(
    score_arrays: List[np.ndarray], cfg: Optional[ThresholdConfig] = None
) -> List[ThresholdResult]:
    return [select_threshold(s, cfg) for s in score_arrays]

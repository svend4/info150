"""Score normalization primitives.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/score_normalizer.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Upstream normalizes matcher scores across many torn-document fragments.
- triage4 reuses the same primitives to bring diverse signature scores
  (bleeding, perfusion, chest motion, posture) onto a comparable scale
  before weighted fusion. Particularly useful when per-signal noise
  characteristics differ across sensing modalities.
- Error strings translated to English; behaviour unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class ScoreNormResult:
    scores: np.ndarray
    method: str
    original_min: float
    original_max: float
    params: Dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"ScoreNormResult(method={self.method!r}, "
            f"n={len(self.scores)}, "
            f"range=[{self.scores.min():.3f}, {self.scores.max():.3f}])"
        )


def normalize_minmax(
    scores: np.ndarray,
    feature_range: Tuple[float, float] = (0.0, 1.0),
    eps: float = 1e-9,
) -> ScoreNormResult:
    """Linear min-max normalization into ``feature_range``."""
    a = np.asarray(scores, dtype=np.float64).ravel()
    low, high = feature_range
    mn, mx = float(a.min()), float(a.max())

    if abs(mx - mn) < eps:
        result = np.full_like(a, fill_value=float(low))
    else:
        result = (a - mn) / (mx - mn) * (high - low) + low

    return ScoreNormResult(
        scores=result,
        method="minmax",
        original_min=mn,
        original_max=mx,
        params={"feature_range": feature_range},
    )


def normalize_zscore(scores: np.ndarray, clip_std: float = 3.0) -> ScoreNormResult:
    """Z-score standardization with outlier clipping, scaled into [0, 1]."""
    a = np.asarray(scores, dtype=np.float64).ravel()
    mn, mx = float(a.min()), float(a.max())
    mu = a.mean()
    sigma = a.std()

    if sigma < 1e-9:
        result = np.full_like(a, fill_value=0.5)
    else:
        z = (a - mu) / sigma
        z = np.clip(z, -clip_std, clip_std)
        result = (z + clip_std) / (2.0 * clip_std)

    return ScoreNormResult(
        scores=result,
        method="zscore",
        original_min=mn,
        original_max=mx,
        params={"clip_std": clip_std},
    )


def normalize_rank(scores: np.ndarray) -> ScoreNormResult:
    """Rank normalization: 0/(N-1), 1/(N-1), …, 1. Ties get mean rank."""
    a = np.asarray(scores, dtype=np.float64).ravel()
    n = len(a)
    mn, mx = float(a.min()) if n else 0.0, float(a.max()) if n else 0.0

    if n <= 1:
        return ScoreNormResult(
            scores=np.zeros_like(a), method="rank",
            original_min=mn, original_max=mx,
        )

    if np.std(a) < 1e-9:
        return ScoreNormResult(
            scores=np.full(n, 0.5, dtype=np.float64), method="rank",
            original_min=mn, original_max=mx,
        )

    order = np.argsort(a)
    result = np.empty(n, dtype=np.float64)
    result[order] = np.arange(n, dtype=np.float64) / float(n - 1)

    return ScoreNormResult(
        scores=result,
        method="rank",
        original_min=mn,
        original_max=mx,
    )


def calibrate_scores(
    scores: np.ndarray, reference: np.ndarray, n_bins: int = 256
) -> ScoreNormResult:
    """Histogram-matching calibration against a reference distribution."""
    s = np.asarray(scores, dtype=np.float64).ravel()
    ref = np.asarray(reference, dtype=np.float64).ravel()

    if s.size == 0 or ref.size == 0:
        mn = float(s.min()) if s.size > 0 else 0.0
        mx = float(s.max()) if s.size > 0 else 0.0
        return ScoreNormResult(
            scores=s.copy(), method="calibrated",
            original_min=mn, original_max=mx,
        )

    mn, mx = float(s.min()), float(s.max())
    s_sorted = np.sort(s)
    ref_sorted = np.sort(ref)
    n_s = len(s_sorted)
    n_ref = len(ref_sorted)

    quantiles = np.searchsorted(s_sorted, s, side="right").astype(np.float64)
    quantiles /= float(n_s)
    ref_indices = (quantiles * (n_ref - 1)).astype(int)
    ref_indices = np.clip(ref_indices, 0, n_ref - 1)
    result = ref_sorted[ref_indices]

    return ScoreNormResult(
        scores=result,
        method="calibrated",
        original_min=mn,
        original_max=mx,
        params={"n_bins": n_bins},
    )


def combine_scores(
    score_arrays: List[np.ndarray],
    weights: Optional[List[float]] = None,
    method: str = "weighted",
) -> np.ndarray:
    """Combine several 1-D score vectors of equal length."""
    if not score_arrays:
        raise ValueError("score_arrays must not be empty")
    if method not in ("weighted", "min", "max", "product"):
        raise ValueError(
            f"unknown method {method!r}, "
            f"choose 'weighted', 'min', 'max', or 'product'"
        )

    arrays = [np.asarray(a, dtype=np.float64).ravel() for a in score_arrays]
    n = len(arrays[0])
    for i, a in enumerate(arrays[1:], 1):
        if len(a) != n:
            raise ValueError(
                f"arrays must share length; arrays[0] is {n}, arrays[{i}] is {len(a)}"
            )

    if method == "min":
        return np.min(np.stack(arrays), axis=0)
    if method == "max":
        return np.max(np.stack(arrays), axis=0)
    if method == "product":
        result = np.ones(n, dtype=np.float64)
        for a in arrays:
            result *= a
        return result

    if weights is None:
        w = np.full(len(arrays), 1.0 / len(arrays))
    else:
        w = np.array(weights, dtype=np.float64)
        s = w.sum()
        if s < 1e-9:
            raise ValueError("sum of weights must be > 0")
        w /= s
    return sum(float(wi) * a for wi, a in zip(w, arrays))


def normalize_score_matrix(
    matrix: np.ndarray, method: str = "minmax", keep_diagonal: bool = True
) -> np.ndarray:
    """Normalise only off-diagonal elements of a square score matrix."""
    if method not in ("minmax", "zscore", "rank"):
        raise ValueError(
            f"unknown method {method!r}, choose 'minmax', 'zscore', or 'rank'"
        )

    n = matrix.shape[0]
    if matrix.ndim != 2 or matrix.shape[1] != n:
        raise ValueError(f"matrix must be square, got shape {matrix.shape}")

    m = matrix.astype(np.float64)
    mask_off = ~np.eye(n, dtype=bool)
    off_vals = m[mask_off]

    if method == "minmax":
        r = normalize_minmax(off_vals).scores
    elif method == "zscore":
        r = normalize_zscore(off_vals).scores
    else:
        r = normalize_rank(off_vals).scores

    result = m.copy()
    result[mask_off] = r
    if keep_diagonal:
        np.copyto(result, m, where=np.eye(n, dtype=bool))
    return result


def batch_normalize_scores(
    score_list: List[np.ndarray], method: str = "minmax", **kwargs
) -> List[ScoreNormResult]:
    """Apply the same normalization to each array in a list independently."""
    if method not in ("minmax", "zscore", "rank"):
        raise ValueError(
            f"unknown method {method!r}, choose 'minmax', 'zscore', or 'rank'"
        )

    table: dict[str, Callable[..., ScoreNormResult]] = {
        "minmax": normalize_minmax,
        "zscore": normalize_zscore,
        "rank": normalize_rank,
    }
    fn = table[method]
    return [fn(s, **kwargs) for s in score_list]

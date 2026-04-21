"""Orientation-histogram matching for fragments or regions.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/orient_matcher.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Copied verbatim; error strings translated to English.
- Upstream computes orientation histograms of document-edge fragments.
  In triage4, the same Sobel-gradient histogram describes the orientation
  distribution of a casualty silhouette / wound region / posture patch,
  so the downstream signatures can be aligned to a common axis (gravity,
  body axis, camera horizon).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class OrientConfig:
    n_bins: int = 36
    angle_step: float = 10.0
    max_angle: float = 180.0
    normalize: bool = True
    use_flip: bool = False

    def __post_init__(self) -> None:
        if self.n_bins < 2:
            raise ValueError(f"n_bins must be >= 2, got {self.n_bins}")
        if self.angle_step <= 0:
            raise ValueError(f"angle_step must be > 0, got {self.angle_step}")
        if self.max_angle < 0:
            raise ValueError(f"max_angle must be >= 0, got {self.max_angle}")


@dataclass
class OrientProfile:
    fragment_id: int
    histogram: np.ndarray
    dominant: float

    def __post_init__(self) -> None:
        if self.fragment_id < 0:
            raise ValueError(
                f"fragment_id must be >= 0, got {self.fragment_id}"
            )
        if self.histogram.ndim != 1:
            raise ValueError("histogram must be a 1-D array")
        if len(self.histogram) < 2:
            raise ValueError(
                f"histogram must have >= 2 elements, got {len(self.histogram)}"
            )
        if not (0.0 <= self.dominant < 360.0):
            raise ValueError(
                f"dominant must be in [0, 360), got {self.dominant}"
            )

    @property
    def n_bins(self) -> int:
        return len(self.histogram)

    @property
    def is_uniform(self) -> bool:
        if self.histogram.sum() < 1e-12:
            return True
        norm = self.histogram / (self.histogram.sum() + 1e-12)
        return float(norm.std()) < 0.05


@dataclass
class OrientMatchResult:
    pair: Tuple[int, int]
    best_angle: float
    best_score: float
    angle_scores: Dict[float, float] = field(default_factory=dict)
    is_flipped: bool = False

    def __post_init__(self) -> None:
        if not (0.0 <= self.best_score <= 1.0):
            raise ValueError(
                f"best_score must be in [0, 1], got {self.best_score}"
            )

    @property
    def fragment_a(self) -> int:
        return self.pair[0]

    @property
    def fragment_b(self) -> int:
        return self.pair[1]

    @property
    def n_angles_tested(self) -> int:
        return len(self.angle_scores)


def _histogram_intersection(a: np.ndarray, b: np.ndarray) -> float:
    a_sum = a.sum()
    b_sum = b.sum()
    if a_sum < 1e-12 or b_sum < 1e-12:
        return 0.0
    a_n = a / a_sum
    b_n = b / b_sum
    return float(np.minimum(a_n, b_n).sum())


def _shift_histogram(hist: np.ndarray, bins: int) -> np.ndarray:
    return np.roll(hist, bins)


def compute_orient_profile(
    image: np.ndarray,
    fragment_id: int = 0,
    cfg: Optional[OrientConfig] = None,
) -> OrientProfile:
    if cfg is None:
        cfg = OrientConfig()
    if image.ndim not in (2, 3):
        raise ValueError("image must be a 2-D or 3-D array")

    gray = np.mean(image, axis=2).astype(float) if image.ndim == 3 else image.astype(float)

    gx = np.gradient(gray, axis=1)
    gy = np.gradient(gray, axis=0)

    angles = (np.degrees(np.arctan2(gy, gx)) + 360.0) % 360.0
    magnitudes = np.sqrt(gx ** 2 + gy ** 2)

    hist, _ = np.histogram(
        angles.ravel(),
        bins=cfg.n_bins,
        range=(0.0, 360.0),
        weights=magnitudes.ravel(),
    )
    hist = hist.astype(float)

    if cfg.normalize and hist.sum() > 1e-12:
        hist = hist / hist.sum()

    dominant_bin = int(np.argmax(hist))
    dominant = float(dominant_bin / cfg.n_bins * 360.0)

    return OrientProfile(
        fragment_id=fragment_id, histogram=hist, dominant=dominant
    )


def orient_similarity(
    profile_a: OrientProfile,
    profile_b: OrientProfile,
    angle_deg: float = 0.0,
    cfg: Optional[OrientConfig] = None,
) -> float:
    if cfg is None:
        cfg = OrientConfig()
    n = profile_a.n_bins
    shift_bins = int(round(angle_deg / 360.0 * n)) % n
    shifted_b = _shift_histogram(profile_b.histogram, shift_bins)
    return _histogram_intersection(profile_a.histogram, shifted_b)


def best_orient_angle(
    profile_a: OrientProfile,
    profile_b: OrientProfile,
    cfg: Optional[OrientConfig] = None,
) -> Tuple[float, float]:
    if cfg is None:
        cfg = OrientConfig()
    if cfg.angle_step <= 0:
        raise ValueError("angle_step must be > 0")

    best_angle = 0.0
    best_score = -1.0
    angle = 0.0
    while angle <= cfg.max_angle:
        score = orient_similarity(profile_a, profile_b, angle, cfg)
        if score > best_score:
            best_score = score
            best_angle = angle
        angle += cfg.angle_step

    return best_angle, float(np.clip(best_score, 0.0, 1.0))


def match_orient_pair(
    profile_a: OrientProfile,
    profile_b: OrientProfile,
    cfg: Optional[OrientConfig] = None,
) -> OrientMatchResult:
    if cfg is None:
        cfg = OrientConfig()

    angle_scores: Dict[float, float] = {}
    best_angle = 0.0
    best_score = -1.0
    is_flipped = False

    angle = 0.0
    while angle <= cfg.max_angle:
        score = orient_similarity(profile_a, profile_b, angle, cfg)
        angle_scores[angle] = float(score)
        if score > best_score:
            best_score = score
            best_angle = angle
        angle += cfg.angle_step

    if cfg.use_flip:
        flipped_hist = np.flip(profile_b.histogram)
        flipped_profile = OrientProfile(
            fragment_id=profile_b.fragment_id,
            histogram=flipped_hist,
            dominant=profile_b.dominant,
        )
        angle = 0.0
        while angle <= cfg.max_angle:
            score = orient_similarity(profile_a, flipped_profile, angle, cfg)
            flip_key = -(angle + 1.0)
            angle_scores[flip_key] = float(score)
            if score > best_score:
                best_score = score
                best_angle = angle
                is_flipped = True
            angle += cfg.angle_step

    return OrientMatchResult(
        pair=(profile_a.fragment_id, profile_b.fragment_id),
        best_angle=best_angle,
        best_score=float(np.clip(best_score, 0.0, 1.0)),
        angle_scores=angle_scores,
        is_flipped=is_flipped,
    )


def batch_orient_match(
    profiles: List[OrientProfile],
    cfg: Optional[OrientConfig] = None,
) -> List[OrientMatchResult]:
    results: List[OrientMatchResult] = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            results.append(match_orient_pair(profiles[i], profiles[j], cfg))
    return results

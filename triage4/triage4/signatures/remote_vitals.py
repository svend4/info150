"""Remote vitals via Eulerian video magnification.

Part of Phase 9a (innovation pack, idea #1). Extracts heart-rate and
respiration-rate-band signals from a stack of RGB frames centred on a
skin / torso region — so ``VitalsEstimator`` can work at stand-off range
from a normal camera, not only from contact or thermal sensors.

Based on the Eulerian video-magnification idea (Wu et al., MIT CSAIL,
2012). This implementation keeps only the temporal-filtering step:
we care about the *signal* pulled from the ROI, not the visualised
magnified video. That makes the whole module ~80 lines of scipy.

Pipeline:
    frames[T, H, W, C?]
    → spatially pool each frame to one scalar (mean luminance over ROI)
    → butterworth bandpass filter in vitals band
    → return the cleaned temporal signal

Typical use:
    >>> extractor = EulerianVitalsExtractor()
    >>> pulse = extractor.extract_pulse(face_patch_stack, fs_hz=30.0)
    >>> bpm = VitalsEstimator().estimate([], pulse, fs_hz=30.0).heart_rate_bpm
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from scipy.signal import butter, filtfilt


@dataclass
class EulerianConfig:
    """Bandpass parameters (two default sets for HR and RR)."""

    hr_band_hz: tuple[float, float] = (0.8, 3.5)
    rr_band_hz: tuple[float, float] = (0.15, 0.5)
    filter_order: int = 3

    def __post_init__(self) -> None:
        if self.filter_order < 1:
            raise ValueError(f"filter_order must be >= 1, got {self.filter_order}")
        for name, band in (("hr_band_hz", self.hr_band_hz), ("rr_band_hz", self.rr_band_hz)):
            lo, hi = band
            if not (0.0 < lo < hi):
                raise ValueError(f"{name} must satisfy 0 < low < high, got {band}")


def _spatial_pool(frames: np.ndarray) -> np.ndarray:
    """Reduce each frame to a scalar luminance."""
    arr = np.asarray(frames, dtype=np.float64)
    if arr.ndim == 4:
        # (T, H, W, C) → luminance approximation (Rec. 601)
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        y = 0.299 * r + 0.587 * g + 0.114 * b
        return y.mean(axis=(1, 2))
    if arr.ndim == 3:
        return arr.mean(axis=(1, 2))
    if arr.ndim == 1:
        return arr
    raise ValueError(f"frames must be 1-D, 3-D (T,H,W) or 4-D (T,H,W,C); got shape {arr.shape}")


def _bandpass(signal: np.ndarray, fs_hz: float, band: tuple[float, float], order: int) -> np.ndarray:
    nyq = 0.5 * fs_hz
    lo = band[0] / nyq
    hi = band[1] / nyq
    if not (0.0 < lo < hi < 1.0):
        raise ValueError(
            f"band {band} Hz invalid for fs={fs_hz} Hz (lo={lo}, hi={hi})"
        )
    # Effective minimum sample count for filtfilt with Butterworth of given order.
    pad_len = 3 * (order * 2 + 1)
    if len(signal) <= pad_len:
        return np.zeros_like(signal)
    b, a = butter(order, [lo, hi], btype="bandpass")
    return filtfilt(b, a, signal)


class EulerianVitalsExtractor:
    """Bandpass-filtered scalar signal from a ROI video stack."""

    def __init__(self, cfg: EulerianConfig | None = None) -> None:
        self.cfg = cfg or EulerianConfig()

    def extract_pulse(
        self, frames: Iterable, fs_hz: float = 30.0
    ) -> np.ndarray:
        """Return an HR-band signal (heart-rate band)."""
        pooled = _spatial_pool(np.asarray(frames))
        return _bandpass(pooled, fs_hz, self.cfg.hr_band_hz, self.cfg.filter_order)

    def extract_breathing(
        self, frames: Iterable, fs_hz: float = 30.0
    ) -> np.ndarray:
        """Return an RR-band signal (respiration band)."""
        pooled = _spatial_pool(np.asarray(frames))
        return _bandpass(pooled, fs_hz, self.cfg.rr_band_hz, self.cfg.filter_order)

    def raw_luminance(self, frames: Iterable) -> np.ndarray:
        """No filtering — just spatial pool. For diagnostics / unit-testing."""
        return _spatial_pool(np.asarray(frames))

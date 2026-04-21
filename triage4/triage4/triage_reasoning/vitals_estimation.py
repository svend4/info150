"""Vitals estimation — DARPA Gate 4 capability.

Part of triage4 Phase 7. Estimates heart rate and respiration rate from
short time-series extracted by upstream signature modules:

- respiration rate (RR, breaths per minute) from the chest-motion /
  breathing curve (low-frequency band ~0.15–0.5 Hz ≈ 9–30 brpm);
- heart rate (HR, beats per minute) from the perfusion / skin-color
  series (band ~0.8–3.5 Hz ≈ 48–210 bpm).

The estimator uses FFT peak detection with a band-pass window. If the
signal is too short, uniform, or the signal-to-noise ratio of the peak
is low, the confidence field reflects that.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass
class VitalsEstimate:
    heart_rate_bpm: float
    respiration_rate_bpm: float
    hr_confidence: float
    rr_confidence: float

    def __post_init__(self) -> None:
        for name, val in (
            ("heart_rate_bpm", self.heart_rate_bpm),
            ("respiration_rate_bpm", self.respiration_rate_bpm),
        ):
            if val < 0.0:
                raise ValueError(f"{name} must be >= 0, got {val}")
        for name, val in (
            ("hr_confidence", self.hr_confidence),
            ("rr_confidence", self.rr_confidence),
        ):
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {val}")


def _band_peak(
    series: Sequence[float],
    fs_hz: float,
    f_low: float,
    f_high: float,
) -> tuple[float, float]:
    """Return (peak_frequency_hz, confidence) via FFT within a band."""
    arr = np.asarray(list(series), dtype=np.float64)
    n = len(arr)
    if n < 8 or fs_hz <= 0.0:
        return 0.0, 0.0

    arr = arr - arr.mean()
    if np.allclose(arr, 0.0):
        return 0.0, 0.0

    freqs = np.fft.rfftfreq(n, d=1.0 / fs_hz)
    spectrum = np.abs(np.fft.rfft(arr))

    band_mask = (freqs >= f_low) & (freqs <= f_high)
    if not band_mask.any() or spectrum[band_mask].sum() == 0.0:
        return 0.0, 0.0

    peak_idx = int(np.argmax(spectrum * band_mask))
    peak_freq = float(freqs[peak_idx])
    peak_power = float(spectrum[peak_idx])

    # Confidence = how much of the in-band energy concentrates at the peak.
    band_energy = float(spectrum[band_mask].sum())
    confidence = min(1.0, peak_power / (band_energy + 1e-12) * 2.0) if band_energy > 0 else 0.0

    return peak_freq, confidence


class VitalsEstimator:
    """Estimate HR and RR from breathing and perfusion time series."""

    def __init__(
        self,
        rr_band_hz: tuple[float, float] = (0.15, 0.5),
        hr_band_hz: tuple[float, float] = (0.8, 3.5),
    ) -> None:
        self.rr_band_hz = rr_band_hz
        self.hr_band_hz = hr_band_hz

    def estimate(
        self,
        breathing_curve: Sequence[float],
        perfusion_series: Sequence[float],
        fs_hz: float = 30.0,
    ) -> VitalsEstimate:
        rr_freq, rr_conf = _band_peak(
            breathing_curve, fs_hz, *self.rr_band_hz
        )
        hr_freq, hr_conf = _band_peak(
            perfusion_series, fs_hz, *self.hr_band_hz
        )

        return VitalsEstimate(
            heart_rate_bpm=round(hr_freq * 60.0, 1),
            respiration_rate_bpm=round(rr_freq * 60.0, 1),
            hr_confidence=round(hr_conf, 3),
            rr_confidence=round(rr_conf, 3),
        )

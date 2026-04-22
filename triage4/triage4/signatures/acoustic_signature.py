"""Bioacoustic signatures — cough / wheeze / groan detection.

Part of Phase 9c (innovation pack 2, idea #7). Existing triage4
signature channels are all visual or thermal. Audio is underused: a
microphone on a drone or quadruped catches weak acoustic signals that
complement the visual channels.

This module is deliberately simple — **no deep model**, only bandpower
in frequency ranges that characterise the target sounds. Cough, wheeze
and groan have distinct spectral footprints (cough is broadband +
short; wheeze is narrowband 400–1000 Hz sustained; groan is low-frequency
100–300 Hz sustained). Each becomes a probability score in [0, 1].
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class AcousticSignature:
    has_cough: float
    has_wheeze: float
    has_groan: float
    has_silence: float
    broadband_power: float
    quality_score: float


def _bandpower(
    audio: np.ndarray, fs_hz: float, band: tuple[float, float]
) -> float:
    n = len(audio)
    if n == 0 or fs_hz <= 0:
        return 0.0
    signal = audio - audio.mean()
    spectrum = np.abs(np.fft.rfft(signal)) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0 / fs_hz)
    mask = (freqs >= band[0]) & (freqs <= band[1])
    if not mask.any():
        return 0.0
    total = float(spectrum.sum())
    if total <= 0.0:
        return 0.0
    return float(spectrum[mask].sum() / total)


class AcousticSignatureExtractor:
    """Bandpower-based cough / wheeze / groan scorer."""

    def __init__(
        self,
        cough_band: tuple[float, float] = (300.0, 3000.0),
        wheeze_band: tuple[float, float] = (400.0, 1000.0),
        groan_band: tuple[float, float] = (80.0, 300.0),
        min_fs_hz: float = 8000.0,
    ) -> None:
        if min_fs_hz < 2 * max(cough_band[1], wheeze_band[1]):
            raise ValueError(
                f"min_fs_hz ({min_fs_hz}) must cover at least 2× highest band"
            )
        self.cough_band = cough_band
        self.wheeze_band = wheeze_band
        self.groan_band = groan_band
        self.min_fs_hz = float(min_fs_hz)

    def extract(self, audio: np.ndarray, fs_hz: float) -> AcousticSignature:
        arr = np.asarray(audio, dtype=np.float64).ravel()
        if len(arr) < 16 or fs_hz < self.min_fs_hz:
            return AcousticSignature(
                has_cough=0.0,
                has_wheeze=0.0,
                has_groan=0.0,
                has_silence=1.0,
                broadband_power=0.0,
                quality_score=0.0,
            )

        peak = float(np.max(np.abs(arr)))
        if peak < 1e-6:
            return AcousticSignature(
                has_cough=0.0,
                has_wheeze=0.0,
                has_groan=0.0,
                has_silence=1.0,
                broadband_power=0.0,
                quality_score=0.2,
            )

        normalised = arr / peak
        broadband = float(np.sqrt(np.mean(normalised ** 2)))

        cough_p = _bandpower(normalised, fs_hz, self.cough_band)
        wheeze_p = _bandpower(normalised, fs_hz, self.wheeze_band)
        groan_p = _bandpower(normalised, fs_hz, self.groan_band)

        # Cough is broadband + loud: combine band-dominance with amplitude.
        has_cough = min(1.0, cough_p * (1.0 + 2.0 * broadband))
        # Wheeze is narrowband sustained energy.
        has_wheeze = min(1.0, wheeze_p * 2.5)
        # Groan is low-frequency sustained energy.
        has_groan = min(1.0, groan_p * 2.5)
        has_silence = max(0.0, 1.0 - broadband * 4.0)

        quality = min(1.0, max(0.2, 0.4 + broadband * 1.5))

        return AcousticSignature(
            has_cough=round(has_cough, 3),
            has_wheeze=round(has_wheeze, 3),
            has_groan=round(has_groan, 3),
            has_silence=round(has_silence, 3),
            broadband_power=round(broadband, 3),
            quality_score=round(quality, 3),
        )

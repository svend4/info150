import numpy as np
import pytest

from triage4.triage_reasoning import VitalsEstimate, VitalsEstimator


def _sinusoid(freq_hz: float, fs_hz: float, seconds: float = 6.0) -> list[float]:
    n = int(seconds * fs_hz)
    t = np.arange(n) / fs_hz
    return list(np.sin(2 * np.pi * freq_hz * t))


def test_vitals_recovers_respiration_rate():
    est = VitalsEstimator()
    # 15 breaths per minute = 0.25 Hz. With 6 s at 30 Hz the FFT bin width
    # is ~0.167 Hz (≈10 bpm) so we only check a broad band around 15 bpm.
    breathing = _sinusoid(0.25, fs_hz=30.0, seconds=10.0)
    result = est.estimate(breathing, perfusion_series=[0.0] * 200, fs_hz=30.0)
    assert isinstance(result, VitalsEstimate)
    assert 9.0 <= result.respiration_rate_bpm <= 21.0
    assert result.rr_confidence > 0.1


def test_vitals_recovers_heart_rate():
    est = VitalsEstimator()
    # 72 bpm = 1.2 Hz
    perfusion = _sinusoid(1.2, fs_hz=30.0)
    result = est.estimate(breathing_curve=[0.0] * 60, perfusion_series=perfusion, fs_hz=30.0)
    assert 60.0 <= result.heart_rate_bpm <= 90.0
    assert result.hr_confidence > 0.1


def test_vitals_empty_input_zero_confidence():
    est = VitalsEstimator()
    result = est.estimate([], [], fs_hz=30.0)
    assert result.heart_rate_bpm == 0.0
    assert result.respiration_rate_bpm == 0.0
    assert result.hr_confidence == 0.0
    assert result.rr_confidence == 0.0


def test_vitals_flat_input_zero_confidence():
    est = VitalsEstimator()
    flat = [0.5] * 120
    result = est.estimate(flat, flat, fs_hz=30.0)
    assert result.hr_confidence == 0.0
    assert result.rr_confidence == 0.0


def test_vitals_too_short_returns_zero():
    est = VitalsEstimator()
    result = est.estimate([0.0, 0.1, 0.2], [0.0, 0.1, 0.2], fs_hz=30.0)
    assert result.heart_rate_bpm == 0.0
    assert result.respiration_rate_bpm == 0.0


def test_vitals_estimate_validates_ranges():
    with pytest.raises(ValueError):
        VitalsEstimate(
            heart_rate_bpm=-1.0,
            respiration_rate_bpm=10.0,
            hr_confidence=0.5,
            rr_confidence=0.5,
        )
    with pytest.raises(ValueError):
        VitalsEstimate(
            heart_rate_bpm=60.0,
            respiration_rate_bpm=10.0,
            hr_confidence=1.5,
            rr_confidence=0.5,
        )

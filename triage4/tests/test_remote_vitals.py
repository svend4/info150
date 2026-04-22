import numpy as np
import pytest

from triage4.signatures import EulerianConfig, EulerianVitalsExtractor
from triage4.triage_reasoning import VitalsEstimator


def _fake_video_with_pulse(
    n_frames: int,
    freq_hz: float,
    fs_hz: float,
    h: int = 6,
    w: int = 6,
    noise: float = 0.0,
    seed: int = 0,
) -> np.ndarray:
    """(T, H, W, 3) stack whose mean luminance oscillates at freq_hz."""
    t = np.arange(n_frames) / fs_hz
    base = 128.0 + 10.0 * np.sin(2 * np.pi * freq_hz * t)
    rng = np.random.default_rng(seed)
    stack = np.empty((n_frames, h, w, 3), dtype=np.float64)
    for i, b in enumerate(base):
        frame = np.full((h, w), b)
        if noise > 0:
            frame = frame + rng.normal(0, noise, (h, w))
        stack[i, ..., 0] = frame
        stack[i, ..., 1] = frame
        stack[i, ..., 2] = frame
    return stack


def test_eulerian_config_validates():
    with pytest.raises(ValueError):
        EulerianConfig(filter_order=0)
    with pytest.raises(ValueError):
        EulerianConfig(hr_band_hz=(2.0, 1.0))
    with pytest.raises(ValueError):
        EulerianConfig(rr_band_hz=(-0.1, 0.5))


def test_raw_luminance_shape_matches_time_axis():
    stack = _fake_video_with_pulse(n_frames=60, freq_hz=1.2, fs_hz=30.0)
    out = EulerianVitalsExtractor().raw_luminance(stack)
    assert out.shape == (60,)


def test_extract_pulse_recovers_sinusoid_in_hr_band():
    # 72 bpm = 1.2 Hz
    stack = _fake_video_with_pulse(n_frames=300, freq_hz=1.2, fs_hz=30.0)
    pulse = EulerianVitalsExtractor().extract_pulse(stack, fs_hz=30.0)
    # Hand off to existing FFT-based VitalsEstimator. The HR band search
    # should concentrate energy around 72 bpm.
    vitals = VitalsEstimator().estimate(
        breathing_curve=[0.0] * len(pulse),
        perfusion_series=pulse.tolist(),
        fs_hz=30.0,
    )
    assert 60.0 <= vitals.heart_rate_bpm <= 90.0
    assert vitals.hr_confidence > 0.1


def test_extract_breathing_recovers_rr_band_signal():
    # 18 bpm = 0.3 Hz
    stack = _fake_video_with_pulse(n_frames=300, freq_hz=0.3, fs_hz=30.0)
    rr_signal = EulerianVitalsExtractor().extract_breathing(stack, fs_hz=30.0)
    vitals = VitalsEstimator().estimate(
        breathing_curve=rr_signal.tolist(),
        perfusion_series=[0.0] * len(rr_signal),
        fs_hz=30.0,
    )
    assert 12.0 <= vitals.respiration_rate_bpm <= 25.0


def test_short_input_returns_zero_output():
    stack = _fake_video_with_pulse(n_frames=10, freq_hz=1.2, fs_hz=30.0)
    pulse = EulerianVitalsExtractor().extract_pulse(stack, fs_hz=30.0)
    # 10 samples is below the filtfilt pad-length; implementation should
    # return all zeros instead of raising.
    assert np.allclose(pulse, 0.0)


def test_invalid_band_for_sampling_rate_raises():
    stack = _fake_video_with_pulse(n_frames=60, freq_hz=1.2, fs_hz=3.0)
    # 3 Hz sample rate cannot carry 1.0..3.5 Hz band (above Nyquist).
    with pytest.raises(ValueError):
        EulerianVitalsExtractor().extract_pulse(stack, fs_hz=3.0)


def test_accepts_grayscale_stack():
    gray = _fake_video_with_pulse(n_frames=60, freq_hz=1.2, fs_hz=30.0)[..., 0]
    out = EulerianVitalsExtractor().raw_luminance(gray)
    assert out.shape == (60,)


def test_noise_reduces_hr_confidence():
    clean = _fake_video_with_pulse(n_frames=300, freq_hz=1.2, fs_hz=30.0)
    noisy = _fake_video_with_pulse(
        n_frames=300, freq_hz=1.2, fs_hz=30.0, noise=30.0
    )
    p_clean = EulerianVitalsExtractor().extract_pulse(clean, fs_hz=30.0)
    p_noisy = EulerianVitalsExtractor().extract_pulse(noisy, fs_hz=30.0)
    est = VitalsEstimator()
    conf_clean = est.estimate([], p_clean.tolist(), fs_hz=30.0).hr_confidence
    conf_noisy = est.estimate([], p_noisy.tolist(), fs_hz=30.0).hr_confidence
    assert conf_clean >= conf_noisy

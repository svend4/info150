"""Tests for ``triage4.perception.frame_source``."""

from __future__ import annotations

import numpy as np
import pytest

from triage4.perception.frame_source import (
    FrameSource,
    FrameSourceUnavailable,
    LoopbackFrameSource,
    SyntheticFrameSource,
    build_opencv_frame_source,
)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_loopback_satisfies_frame_source_protocol():
    src = LoopbackFrameSource([np.zeros((2, 2, 3), dtype=np.uint8)])
    assert isinstance(src, FrameSource)


def test_synthetic_satisfies_frame_source_protocol():
    src = SyntheticFrameSource(n_frames=3)
    assert isinstance(src, FrameSource)


# ---------------------------------------------------------------------------
# Loopback
# ---------------------------------------------------------------------------


def test_loopback_yields_frames_in_order():
    frames = [
        np.full((2, 2, 3), i, dtype=np.uint8) for i in range(3)
    ]
    src = LoopbackFrameSource(frames)
    out = [src.read() for _ in range(4)]
    assert [int(f[0, 0, 0]) for f in out[:3]] == [0, 1, 2]
    assert out[3] is None


def test_loopback_rejects_non_ndarray():
    with pytest.raises(TypeError):
        LoopbackFrameSource([None])  # type: ignore[list-item]


def test_loopback_rejects_wrong_shape():
    with pytest.raises(ValueError):
        LoopbackFrameSource([np.zeros((4, 4), dtype=np.uint8)])


def test_loopback_close_stops_reads():
    src = LoopbackFrameSource([np.zeros((2, 2, 3), dtype=np.uint8)])
    src.close()
    assert src.read() is None


def test_loopback_iterator_protocol():
    frames = [np.full((2, 2, 3), i, dtype=np.uint8) for i in range(3)]
    collected = list(LoopbackFrameSource(frames))
    assert len(collected) == 3


def test_loopback_context_manager_closes_on_exit():
    src = LoopbackFrameSource([np.zeros((2, 2, 3), dtype=np.uint8)])
    with src:
        pass
    assert src.read() is None


def test_loopback_reports_frame_count_and_position():
    frames = [np.zeros((2, 2, 3), dtype=np.uint8) for _ in range(5)]
    src = LoopbackFrameSource(frames)
    assert src.frame_count == 5
    assert src.position == 0
    src.read()
    assert src.position == 1


def test_loopback_empty_is_valid():
    src = LoopbackFrameSource([])
    assert src.read() is None
    assert src.frame_count == 0


# ---------------------------------------------------------------------------
# Synthetic — pulse pattern
# ---------------------------------------------------------------------------


def test_synthetic_pulse_luminance_oscillates_at_hr():
    src = SyntheticFrameSource(
        pattern="pulse", n_frames=90, fs_hz=30.0, hr_hz=1.0,
        width=16, height=16, seed=0,
    )
    means = []
    while True:
        frame = src.read()
        if frame is None:
            break
        means.append(float(frame.mean()))
    # 3 full cycles in 3 s → at least 2 extrema.
    peak_to_peak = max(means) - min(means)
    assert peak_to_peak > 2.0  # pulse is 10 units peak-to-peak before noise


def test_synthetic_is_deterministic_under_seed():
    a = SyntheticFrameSource(pattern="pulse", n_frames=5, seed=42)
    b = SyntheticFrameSource(pattern="pulse", n_frames=5, seed=42)
    for _ in range(5):
        fa = a.read()
        fb = b.read()
        np.testing.assert_array_equal(fa, fb)


def test_synthetic_different_seeds_differ():
    a = SyntheticFrameSource(pattern="pulse", n_frames=3, seed=1)
    b = SyntheticFrameSource(pattern="pulse", n_frames=3, seed=2)
    assert not np.array_equal(a.read(), b.read())


def test_synthetic_gradient_is_monotone_on_rows():
    src = SyntheticFrameSource(pattern="gradient", n_frames=1, width=16, height=8)
    frame = src.read()
    # R channel increases left → right.
    row = frame[0, :, 0]
    assert row[0] < row[-1]


def test_synthetic_moving_square_shifts_over_time():
    src = SyntheticFrameSource(
        pattern="moving_square", n_frames=4, width=16, height=8, fs_hz=4.0,
    )
    cols = []
    while True:
        frame = src.read()
        if frame is None:
            break
        # Column index of the brightest pixel on the middle row.
        cols.append(int(frame[frame.shape[0] // 2, :, 0].argmax()))
    assert len(set(cols)) > 1


def test_synthetic_rejects_unknown_pattern():
    with pytest.raises(ValueError):
        SyntheticFrameSource(pattern="spiral")


def test_synthetic_rejects_zero_size():
    with pytest.raises(ValueError):
        SyntheticFrameSource(n_frames=0)
    with pytest.raises(ValueError):
        SyntheticFrameSource(width=0)
    with pytest.raises(ValueError):
        SyntheticFrameSource(height=0)


def test_synthetic_rejects_nonpositive_sampling():
    with pytest.raises(ValueError):
        SyntheticFrameSource(fs_hz=0.0)
    with pytest.raises(ValueError):
        SyntheticFrameSource(hr_hz=-1.0)


def test_synthetic_exhausts_after_n_frames():
    src = SyntheticFrameSource(n_frames=3, width=4, height=4)
    for _ in range(3):
        assert src.read() is not None
    assert src.read() is None


def test_synthetic_context_manager():
    with SyntheticFrameSource(n_frames=3) as src:
        assert src.read() is not None
    assert src.read() is None


# ---------------------------------------------------------------------------
# OpenCV factory — failure modes only (no cv2 in CI)
# ---------------------------------------------------------------------------


def test_opencv_factory_raises_frame_source_unavailable_without_cv2(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def _blocker(name, *args, **kwargs):
        if name == "cv2":
            raise ImportError("simulated: cv2 not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocker)

    with pytest.raises(FrameSourceUnavailable):
        build_opencv_frame_source(0)

"""Tests for triage4_rescue.perception frame sources."""

from __future__ import annotations

import numpy as np
import pytest

from triage4_rescue.perception import (
    FrameSource,
    FrameSourceUnavailable,
    LoopbackFrameSource,
    SyntheticFrameSource,
)


def _frame(value: int = 128) -> np.ndarray:
    return np.full((4, 6, 3), value, dtype=np.uint8)


def test_loopback_yields_frames_in_order():
    src = LoopbackFrameSource([_frame(10), _frame(20), _frame(30)])
    out = []
    while True:
        f = src.read()
        if f is None:
            break
        out.append(int(f.mean()))
    assert out == [10, 20, 30]


def test_loopback_rejects_non_array():
    with pytest.raises(TypeError):
        LoopbackFrameSource(["not-a-frame"])  # type: ignore[list-item]


def test_loopback_rejects_wrong_shape():
    with pytest.raises(ValueError):
        LoopbackFrameSource([np.zeros((4, 4), dtype=np.uint8)])


def test_loopback_returns_none_after_exhaustion():
    src = LoopbackFrameSource([_frame()])
    assert src.read() is not None
    assert src.read() is None


def test_loopback_close_idempotent():
    src = LoopbackFrameSource([_frame()])
    src.close()
    assert src.read() is None
    src.close()


def test_loopback_context_manager():
    with LoopbackFrameSource([_frame(), _frame()]) as src:
        assert src.read() is not None
    assert src.read() is None


def test_synthetic_pulse_default_shape():
    src = SyntheticFrameSource(pattern="pulse", n_frames=5, width=16, height=12)
    f = src.read()
    assert f is not None
    assert f.shape == (12, 16, 3)


def test_synthetic_exhausts_after_n_frames():
    src = SyntheticFrameSource(n_frames=3)
    count = 0
    while src.read() is not None:
        count += 1
    assert count == 3


def test_synthetic_invalid_pattern_raises():
    with pytest.raises(ValueError):
        SyntheticFrameSource(pattern="not-a-pattern")


def test_synthetic_zero_frames_raises():
    with pytest.raises(ValueError):
        SyntheticFrameSource(n_frames=0)


def test_synthetic_deterministic_seed():
    a = SyntheticFrameSource(seed=42, n_frames=2).read()
    b = SyntheticFrameSource(seed=42, n_frames=2).read()
    np.testing.assert_array_equal(a, b)


def test_protocol_satisfied_by_loopback():
    src = LoopbackFrameSource([_frame()])
    assert isinstance(src, FrameSource)


def test_frame_source_unavailable_is_runtime_error():
    assert issubclass(FrameSourceUnavailable, RuntimeError)

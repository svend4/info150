"""Camera-health tracker — frame ticks, drops, state."""

from __future__ import annotations

import time

import pytest

from triage4_coast.ui import camera_health


@pytest.fixture(autouse=True)
def isolated_store():
    camera_health.reset()
    yield
    camera_health.reset()


class TestRecordFrame:
    def test_first_frame_marks_ok(self) -> None:
        camera_health.record_frame("rtsp://test")
        snap = camera_health.snapshot()
        assert len(snap) == 1
        assert snap[0].source == "rtsp://test"
        assert snap[0].state == "ok"
        assert snap[0].frames_seen == 1

    def test_two_frames_compute_fps(self) -> None:
        camera_health.record_frame("rtsp://test")
        time.sleep(0.05)
        camera_health.record_frame("rtsp://test")
        snap = camera_health.snapshot()
        assert snap[0].fps > 0


class TestRecordDrop:
    def test_drop_increments_counter(self) -> None:
        camera_health.record_drop("rtsp://test", "timeout")
        snap = camera_health.snapshot()
        assert snap[0].frames_dropped == 1
        assert snap[0].last_error == "timeout"

    def test_long_error_truncated(self) -> None:
        camera_health.record_drop("rtsp://test", "x" * 500)
        snap = camera_health.snapshot()
        assert snap[0].last_error is not None
        assert len(snap[0].last_error) == 200


class TestState:
    def test_force_state_down(self) -> None:
        camera_health.mark_state("rtsp://test", "down", "open failed")
        snap = camera_health.snapshot()
        assert snap[0].state == "down"
        assert snap[0].last_error == "open failed"

    def test_invalid_state_rejected(self) -> None:
        with pytest.raises(ValueError):
            camera_health.mark_state("rtsp://test", "broken")


class TestSnapshot:
    def test_empty_store(self) -> None:
        assert camera_health.snapshot() == []

    def test_multi_camera(self) -> None:
        camera_health.record_frame("cam1")
        camera_health.record_drop("cam2", "err")
        snap = camera_health.snapshot()
        assert len(snap) == 2
        sources = {s.source for s in snap}
        assert sources == {"cam1", "cam2"}

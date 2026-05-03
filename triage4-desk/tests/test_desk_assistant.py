"""DeskAssistant engine — channel rules + cue generation."""

from __future__ import annotations

import pytest

from triage4_desk.core.models import DeskSession
from triage4_desk.desk_assistant import DeskAssistant
from triage4_desk.sim import demo_session, demo_sessions


@pytest.fixture
def engine() -> DeskAssistant:
    return DeskAssistant()


def _s(**overrides: object) -> DeskSession:
    base: dict[str, object] = dict(
        worker_id="W1",
        work_mode="office",
        session_min=20.0,
        minutes_since_break=10.0,
        minutes_since_stretch=30.0,
        typing_intensity=0.3,
        screen_motion_proxy=0.3,
        ambient_light_proxy=0.5,
        posture_quality=0.9,
        drowsiness_signal=0.0,
        distraction_signal=0.0,
        air_temp_c=22.0,
        hr_bpm=80.0,
    )
    base.update(overrides)
    return DeskSession(**base)  # type: ignore[arg-type]


class TestEngineHappyPath:
    def test_fresh_worker(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(session_min=5.0, minutes_since_break=2.0))
        assert a.posture_advisory == "ok"
        assert a.microbreak_due is False
        assert a.eye_break_due is False
        assert a.overall_safety > 0.7

    def test_demo_session_runs(self, engine: DeskAssistant) -> None:
        a = engine.review(demo_session())
        assert 0.0 <= a.fatigue_index <= 1.0


class TestPomodoro:
    def test_office_25min_break_due(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(work_mode="office", minutes_since_break=30.0))
        assert a.microbreak_due is True

    def test_coding_50min_threshold(self, engine: DeskAssistant) -> None:
        # In coding mode the threshold is 50, so 35 should NOT trigger
        a = engine.review(_s(work_mode="coding", minutes_since_break=35.0))
        assert a.microbreak_due is False

    def test_gaming_30min_threshold(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(work_mode="gaming", minutes_since_break=35.0))
        assert a.microbreak_due is True


class TestEyeBreak:
    def test_20_20_20(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(work_mode="office", session_min=25.0))
        assert a.eye_break_due is True

    def test_short_session_no_eye_break(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(work_mode="office", session_min=5.0))
        assert a.eye_break_due is False


class TestPosture:
    def test_upright(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(posture_quality=0.95))
        assert a.posture_advisory == "ok"

    def test_leaning(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(posture_quality=0.6))
        assert a.posture_advisory == "leaning"

    def test_slumped(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(posture_quality=0.3))
        assert a.posture_advisory == "slumped"


class TestStretch:
    def test_long_session_no_stretch(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(work_mode="office", minutes_since_stretch=120.0))
        assert a.stretch_due is True

    def test_short_session_ok(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(work_mode="office", minutes_since_stretch=30.0))
        assert a.stretch_due is False


class TestHydration:
    def test_long_break_gap(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(minutes_since_break=50.0))
        assert a.hydration_due is True

    def test_warm_office_lower_threshold(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(minutes_since_break=35.0, air_temp_c=26.0))
        assert a.hydration_due is True


class TestDrowsiness:
    def test_high_signal_alerts(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(drowsiness_signal=0.8))
        assert a.drowsiness_alert is True

    def test_low_hr_long_session_alerts(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(session_min=120.0, hr_bpm=50.0))
        assert a.drowsiness_alert is True


class TestDistraction:
    def test_high_signal_alerts(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(distraction_signal=0.85))
        assert a.distraction_alert is True

    def test_low_signal_no_alert(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(distraction_signal=0.2))
        assert a.distraction_alert is False


class TestFatigueScale:
    def test_short_low_intensity(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(
            session_min=10.0, posture_quality=0.95,
            typing_intensity=0.1, drowsiness_signal=0.0,
        ))
        assert a.fatigue_index < 0.3

    def test_long_drowsy_slumped_high_fatigue(
        self, engine: DeskAssistant,
    ) -> None:
        a = engine.review(_s(
            work_mode="gaming", session_min=240.0,
            posture_quality=0.2, typing_intensity=0.9,
            drowsiness_signal=0.7, hr_bpm=125.0,
        ))
        assert a.fatigue_index > 0.7


class TestCues:
    def test_severe_fatigue_cue(self, engine: DeskAssistant) -> None:
        a = engine.review(_s(
            work_mode="gaming", session_min=240.0,
            posture_quality=0.2, drowsiness_signal=0.8,
        ))
        severe = a.cues_at_severity("severe")
        kinds = [c.kind for c in severe]
        assert "fatigue" in kinds or "drowsiness" in kinds or "stretch" in kinds

    def test_demo_sessions_no_crash(self, engine: DeskAssistant) -> None:
        for s in demo_sessions():
            a = engine.review(s)
            assert a is not None

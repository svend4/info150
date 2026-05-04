"""Model validation: DeskSession + DeskAdvisory + CoachCue."""

from __future__ import annotations

import pytest

from triage4_desk.core.models import (
    CoachCue,
    DeskAdvisory,
    DeskSession,
)


def _ok(**overrides: object) -> DeskSession:
    base: dict[str, object] = dict(
        worker_id="W1",
        work_mode="office",
        session_min=35.0,
        minutes_since_break=15.0,
        minutes_since_stretch=60.0,
        typing_intensity=0.4,
        screen_motion_proxy=0.3,
        ambient_light_proxy=0.5,
        posture_quality=0.85,
        drowsiness_signal=0.0,
        distraction_signal=0.0,
        air_temp_c=22.0,
        hr_bpm=78.0,
    )
    base.update(overrides)
    return DeskSession(**base)  # type: ignore[arg-type]


class TestDeskSession:
    def test_happy_path(self) -> None:
        s = _ok()
        assert s.worker_id == "W1"
        assert s.work_mode == "office"

    def test_empty_worker_id(self) -> None:
        with pytest.raises(ValueError, match="worker_id"):
            _ok(worker_id="")

    def test_invalid_work_mode(self) -> None:
        with pytest.raises(ValueError, match="work_mode"):
            _ok(work_mode="napping")

    def test_session_min_range(self) -> None:
        with pytest.raises(ValueError, match="session_min"):
            _ok(session_min=-1)

    def test_posture_quality_range(self) -> None:
        with pytest.raises(ValueError, match="posture_quality"):
            _ok(posture_quality=1.5)

    def test_drowsiness_range(self) -> None:
        with pytest.raises(ValueError, match="drowsiness_signal"):
            _ok(drowsiness_signal=-0.1)

    def test_distraction_range(self) -> None:
        with pytest.raises(ValueError, match="distraction_signal"):
            _ok(distraction_signal=2.0)

    def test_air_temp_optional(self) -> None:
        _ok(air_temp_c=None)

    def test_air_temp_range(self) -> None:
        with pytest.raises(ValueError, match="air_temp_c"):
            _ok(air_temp_c=120.0)

    def test_hr_optional(self) -> None:
        _ok(hr_bpm=None)


class TestCoachCue:
    def test_happy_path(self) -> None:
        c = CoachCue(kind="microbreak", severity="minor", text="take five")
        assert c.kind == "microbreak"

    def test_empty_text(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            CoachCue(kind="fatigue", severity="minor", text="   ")

    @pytest.mark.parametrize(
        "bad_word", ["injured", "diagnose", "treat ", "dangerous", "medical"],
    )
    def test_forbidden_words(self, bad_word: str) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            CoachCue(
                kind="fatigue", severity="minor",
                text=f"You look {bad_word} - slow down.",
            )

    def test_invalid_severity(self) -> None:
        with pytest.raises(ValueError, match="severity"):
            CoachCue(
                kind="fatigue",
                severity="critical",  # type: ignore[arg-type]
                text="...",
            )


class TestDeskAdvisory:
    def test_happy_path(self) -> None:
        s = _ok()
        a = DeskAdvisory(
            session=s,
            fatigue_index=0.3, hydration_due=False, eye_break_due=False,
            microbreak_due=False, stretch_due=False,
            posture_advisory="ok",
            drowsiness_alert=False, distraction_alert=False,
            overall_safety=0.8,
        )
        assert a.fatigue_index == 0.3
        assert a.posture_advisory == "ok"

    def test_invalid_posture_advisory(self) -> None:
        with pytest.raises(ValueError, match="posture_advisory"):
            DeskAdvisory(
                session=_ok(),
                fatigue_index=0.3, hydration_due=False, eye_break_due=False,
                microbreak_due=False, stretch_due=False,
                posture_advisory="moonwalk",  # type: ignore[arg-type]
                drowsiness_alert=False, distraction_alert=False,
                overall_safety=0.8,
            )

    def test_score_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="fatigue_index"):
            DeskAdvisory(
                session=_ok(),
                fatigue_index=1.5, hydration_due=False, eye_break_due=False,
                microbreak_due=False, stretch_due=False,
                posture_advisory="ok",
                drowsiness_alert=False, distraction_alert=False,
                overall_safety=0.8,
            )

    def test_as_text_round_trip(self) -> None:
        a = DeskAdvisory(
            session=_ok(),
            fatigue_index=0.4, hydration_due=True, eye_break_due=True,
            microbreak_due=False, stretch_due=False,
            posture_advisory="leaning",
            drowsiness_alert=False, distraction_alert=False,
            overall_safety=0.7,
        )
        text = a.as_text()
        assert "W1" in text
        assert "office" in text
        assert "hydration_due" in text

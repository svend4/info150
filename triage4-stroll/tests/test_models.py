"""Model validation: StrollSegment + StrollAdvisory + CoachCue."""

from __future__ import annotations

import pytest

from triage4_stroll.core.models import (
    CoachCue,
    StrollAdvisory,
    StrollSegment,
)


def _ok_segment(**overrides: object) -> StrollSegment:
    base: dict[str, object] = dict(
        walker_id="W1",
        terrain="flat",
        pace_kmh=4.5,
        duration_min=20.0,
        activity_intensity=0.4,
        sun_exposure_proxy=0.3,
        minutes_since_rest=10.0,
        air_temp_c=22.0,
        hr_bpm=110.0,
    )
    base.update(overrides)
    return StrollSegment(**base)  # type: ignore[arg-type]


class TestStrollSegment:
    def test_happy_path(self) -> None:
        seg = _ok_segment()
        assert seg.walker_id == "W1"
        assert seg.terrain == "flat"

    def test_empty_walker_id(self) -> None:
        with pytest.raises(ValueError, match="walker_id"):
            _ok_segment(walker_id="")

    def test_invalid_terrain(self) -> None:
        with pytest.raises(ValueError, match="terrain"):
            _ok_segment(terrain="moonscape")

    def test_pace_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="pace_kmh"):
            _ok_segment(pace_kmh=25.0)
        with pytest.raises(ValueError, match="pace_kmh"):
            _ok_segment(pace_kmh=-1.0)

    def test_duration_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="duration_min"):
            _ok_segment(duration_min=-1.0)

    def test_activity_intensity_range(self) -> None:
        with pytest.raises(ValueError, match="activity_intensity"):
            _ok_segment(activity_intensity=1.5)

    def test_sun_exposure_range(self) -> None:
        with pytest.raises(ValueError, match="sun_exposure_proxy"):
            _ok_segment(sun_exposure_proxy=-0.1)

    def test_air_temp_optional(self) -> None:
        _ok_segment(air_temp_c=None)

    def test_air_temp_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="air_temp_c"):
            _ok_segment(air_temp_c=120.0)

    def test_hr_optional(self) -> None:
        _ok_segment(hr_bpm=None)

    def test_hr_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="hr_bpm"):
            _ok_segment(hr_bpm=300.0)


class TestCoachCue:
    def test_happy_path(self) -> None:
        cue = CoachCue(kind="fatigue", severity="minor", text="slow down")
        assert cue.kind == "fatigue"

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            CoachCue(kind="fatigue", severity="minor", text="   ")

    def test_invalid_severity(self) -> None:
        with pytest.raises(ValueError, match="severity"):
            CoachCue(
                kind="fatigue",
                severity="critical",  # type: ignore[arg-type]
                text="...",
            )

    @pytest.mark.parametrize(
        "bad_word", ["injured", "diagnose", "treat ", "dangerous", "medical"],
    )
    def test_forbidden_words(self, bad_word: str) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            CoachCue(
                kind="fatigue",
                severity="minor",
                text=f"You look {bad_word} — slow down.",
            )


class TestStrollAdvisory:
    def test_happy_path(self) -> None:
        seg = _ok_segment()
        adv = StrollAdvisory(
            segment=seg,
            fatigue_index=0.4,
            hydration_due=False,
            shade_advisory=False,
            pace_advisory="continue",
            rest_due=False,
            overall_safety=0.7,
        )
        assert adv.fatigue_index == 0.4
        assert adv.cues == []

    def test_invalid_pace_advisory(self) -> None:
        with pytest.raises(ValueError, match="pace_advisory"):
            StrollAdvisory(
                segment=_ok_segment(),
                fatigue_index=0.4,
                hydration_due=False,
                shade_advisory=False,
                pace_advisory="moonwalk",  # type: ignore[arg-type]
                rest_due=False,
                overall_safety=0.7,
            )

    def test_score_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="fatigue_index"):
            StrollAdvisory(
                segment=_ok_segment(),
                fatigue_index=1.5,
                hydration_due=False,
                shade_advisory=False,
                pace_advisory="continue",
                rest_due=False,
                overall_safety=0.7,
            )

    def test_as_text_round_trip(self) -> None:
        seg = _ok_segment()
        adv = StrollAdvisory(
            segment=seg,
            fatigue_index=0.4,
            hydration_due=True,
            shade_advisory=True,
            pace_advisory="slow_down",
            rest_due=True,
            overall_safety=0.5,
        )
        text = adv.as_text()
        assert "W1" in text
        assert "Fatigue: 0.40" in text
        assert "hydration_due" in text

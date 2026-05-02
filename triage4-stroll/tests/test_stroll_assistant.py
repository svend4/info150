"""StrollAssistant engine — channel rules + cue generation."""

from __future__ import annotations

import pytest

from triage4_stroll.core.models import StrollSegment
from triage4_stroll.sim import demo_segment, demo_segments
from triage4_stroll.walk_assistant import StrollAssistant


@pytest.fixture
def engine() -> StrollAssistant:
    return StrollAssistant()


def _seg(**overrides: object) -> StrollSegment:
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


class TestEngineHappyPath:
    def test_fresh_walker(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(duration_min=5.0, minutes_since_rest=5.0))
        assert adv.pace_advisory == "continue"
        assert adv.rest_due is False
        assert adv.overall_safety > 0.6

    def test_demo_segment_runs(self, engine: StrollAssistant) -> None:
        adv = engine.review(demo_segment())
        assert 0.0 <= adv.fatigue_index <= 1.0


class TestPaceAdvisory:
    def test_too_fast_for_hilly(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(terrain="hilly", pace_kmh=5.5))
        assert adv.pace_advisory == "slow_down"

    def test_too_slow_for_flat(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(pace_kmh=2.5, duration_min=10.0))
        assert adv.pace_advisory == "speed_up"

    def test_high_hr_triggers_slow_down(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(hr_bpm=170.0, pace_kmh=3.0))
        assert adv.pace_advisory == "slow_down"


class TestHydration:
    def test_hot_long_walk(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(
            air_temp_c=28.0, minutes_since_rest=25.0, duration_min=40.0,
        ))
        assert adv.hydration_due is True

    def test_short_walk_no_hydration_flag(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(minutes_since_rest=5.0))
        assert adv.hydration_due is False


class TestShade:
    def test_high_sun_long_walk(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(sun_exposure_proxy=0.9, duration_min=30.0))
        assert adv.shade_advisory is True

    def test_low_sun_no_advisory(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(sun_exposure_proxy=0.2, duration_min=30.0))
        assert adv.shade_advisory is False


class TestRest:
    def test_long_unbroken_walk(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(minutes_since_rest=40.0))
        assert adv.rest_due is True


class TestFatigueScale:
    def test_short_low_intensity_low_fatigue(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(
            duration_min=5.0, activity_intensity=0.1, hr_bpm=85.0,
        ))
        assert adv.fatigue_index < 0.3

    def test_long_high_intensity_high_fatigue(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(
            terrain="stairs", duration_min=80.0,
            activity_intensity=0.9, hr_bpm=160.0,
        ))
        assert adv.fatigue_index > 0.7


class TestCues:
    def test_severe_fatigue_cue(self, engine: StrollAssistant) -> None:
        adv = engine.review(_seg(
            terrain="stairs", duration_min=80.0,
            activity_intensity=0.9, hr_bpm=160.0,
        ))
        severe = adv.cues_at_severity("severe")
        assert any(c.kind == "fatigue" for c in severe)

    def test_demo_segments_no_crash(self, engine: StrollAssistant) -> None:
        for seg in demo_segments():
            adv = engine.review(seg)
            assert adv is not None

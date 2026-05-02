"""CoastSafetyEngine — channel rules + alert generation."""

from __future__ import annotations

import pytest

from triage4_coast.coast_safety import CoastSafetyEngine
from triage4_coast.core.models import CoastZoneObservation
from triage4_coast.sim import demo_coast, generate_zone_observation


@pytest.fixture
def engine() -> CoastSafetyEngine:
    return CoastSafetyEngine()


def _obs(**overrides: object) -> CoastZoneObservation:
    base: dict[str, object] = dict(
        zone_id="Z1",
        zone_kind="beach",
        window_duration_s=60.0,
        density_pressure=0.3,
        in_water_motion=0.0,
        sun_intensity=0.4,
        lost_child_flag=False,
    )
    base.update(overrides)
    return CoastZoneObservation(**base)  # type: ignore[arg-type]


class TestEngineHappyPath:
    def test_demo_coast_runs(self, engine: CoastSafetyEngine) -> None:
        report = engine.review(coast_id="DEMO_COAST", zones=demo_coast())
        assert len(report.scores) == 4
        assert report.coast_id == "DEMO_COAST"

    def test_quiet_beach_is_ok(self, engine: CoastSafetyEngine) -> None:
        report = engine.review(coast_id="C1", zones=[_obs(
            density_pressure=0.15, sun_intensity=0.30,
        )])
        assert report.scores[0].alert_level == "ok"


class TestDrowning:
    def test_water_low_motion_high_density_urgent(
        self, engine: CoastSafetyEngine,
    ) -> None:
        report = engine.review(coast_id="C1", zones=[_obs(
            zone_kind="water", density_pressure=0.85, in_water_motion=0.05,
        )])
        score = report.scores[0]
        assert score.alert_level == "urgent"
        kinds = [a.kind for a in report.alerts]
        assert "drowning" in kinds

    def test_beach_no_drowning_signal(self, engine: CoastSafetyEngine) -> None:
        report = engine.review(coast_id="C1", zones=[_obs(
            zone_kind="beach", density_pressure=0.3, in_water_motion=0.0,
        )])
        kinds = [a.kind for a in report.alerts]
        assert "drowning" not in kinds


class TestDensity:
    def test_promenade_packed_urgent(self, engine: CoastSafetyEngine) -> None:
        report = engine.review(coast_id="C1", zones=[_obs(
            zone_kind="promenade", density_pressure=0.85,
        )])
        kinds = [a.kind for a in report.alerts]
        assert "density" in kinds


class TestSun:
    def test_high_sun_water_zone_alert(self, engine: CoastSafetyEngine) -> None:
        report = engine.review(coast_id="C1", zones=[_obs(
            zone_kind="water", sun_intensity=0.85, in_water_motion=0.6,
            density_pressure=0.3,
        )])
        kinds = [a.kind for a in report.alerts]
        assert "sun" in kinds


class TestLostChild:
    def test_flag_drives_urgent(self, engine: CoastSafetyEngine) -> None:
        report = engine.review(coast_id="C1", zones=[_obs(
            lost_child_flag=True,
        )])
        score = report.scores[0]
        assert score.alert_level == "urgent"
        assert score.lost_child_safety == 0.0


class TestOverall:
    def test_overall_drops_with_alerts(self, engine: CoastSafetyEngine) -> None:
        ok = engine.review(coast_id="C1", zones=[_obs(
            zone_kind="beach", density_pressure=0.1, sun_intensity=0.1,
        )])
        bad = engine.review(coast_id="C1", zones=[_obs(
            zone_kind="water", density_pressure=0.85,
            in_water_motion=0.05, sun_intensity=0.85,
        )])
        assert ok.scores[0].overall > bad.scores[0].overall


class TestSimGenerator:
    def test_generate_zone_observation_validates(self) -> None:
        with pytest.raises(ValueError):
            generate_zone_observation(zone_kind="moon")  # type: ignore[arg-type]

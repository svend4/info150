"""Stage-2B channel rules: fall_event, stationary_person, flow_anomaly, slip_risk."""

from __future__ import annotations

import pytest

from triage4_coast.coast_safety import CoastSafetyEngine
from triage4_coast.core.models import CoastZoneObservation


@pytest.fixture
def engine() -> CoastSafetyEngine:
    return CoastSafetyEngine()


def _obs(**overrides: object) -> CoastZoneObservation:
    base: dict[str, object] = dict(
        zone_id="Z1", zone_kind="promenade",
        window_duration_s=60.0,
        density_pressure=0.2, in_water_motion=0.0,
        sun_intensity=0.3, lost_child_flag=False,
    )
    base.update(overrides)
    return CoastZoneObservation(**base)  # type: ignore[arg-type]


class TestFallEvent:
    def test_flag_drives_urgent(self, engine: CoastSafetyEngine) -> None:
        rep = engine.review(coast_id="C1", zones=[_obs(fall_event_flag=True)])
        assert rep.scores[0].alert_level == "urgent"
        assert rep.scores[0].fall_event_safety == 0.0
        kinds = [a.kind for a in rep.alerts]
        assert "fall_event" in kinds

    def test_no_flag_safety_one(self, engine: CoastSafetyEngine) -> None:
        rep = engine.review(coast_id="C1", zones=[_obs()])
        assert rep.scores[0].fall_event_safety == 1.0


class TestStationaryPerson:
    def test_high_signal_urgent(self, engine: CoastSafetyEngine) -> None:
        rep = engine.review(coast_id="C1", zones=[_obs(
            stationary_person_signal=0.85,
        )])
        assert rep.scores[0].alert_level == "urgent"
        kinds = [a.kind for a in rep.alerts]
        assert "stationary_person" in kinds

    def test_mid_signal_watch(self, engine: CoastSafetyEngine) -> None:
        rep = engine.review(coast_id="C1", zones=[_obs(
            stationary_person_signal=0.5,
        )])
        kinds = [a.kind for a in rep.alerts]
        assert "stationary_person" in kinds

    def test_low_signal_no_alert(self, engine: CoastSafetyEngine) -> None:
        rep = engine.review(coast_id="C1", zones=[_obs(
            stationary_person_signal=0.1,
        )])
        kinds = [a.kind for a in rep.alerts]
        assert "stationary_person" not in kinds


class TestFlowAnomaly:
    def test_high_signal_urgent(self, engine: CoastSafetyEngine) -> None:
        rep = engine.review(coast_id="C1", zones=[_obs(
            flow_anomaly_signal=0.85,
        )])
        assert rep.scores[0].alert_level == "urgent"
        kinds = [a.kind for a in rep.alerts]
        assert "flow_anomaly" in kinds


class TestSlipRisk:
    def test_high_signal_urgent(self, engine: CoastSafetyEngine) -> None:
        rep = engine.review(coast_id="C1", zones=[_obs(
            slip_risk_signal=0.9,
        )])
        assert rep.scores[0].alert_level == "urgent"
        kinds = [a.kind for a in rep.alerts]
        assert "slip_risk" in kinds


class TestRangeValidation:
    def test_signal_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="stationary_person_signal"):
            _obs(stationary_person_signal=1.5)
        with pytest.raises(ValueError, match="flow_anomaly_signal"):
            _obs(flow_anomaly_signal=-0.1)
        with pytest.raises(ValueError, match="slip_risk_signal"):
            _obs(slip_risk_signal=2.0)


class TestOverallWeights:
    def test_all_channels_safe_overall_high(
        self, engine: CoastSafetyEngine,
    ) -> None:
        rep = engine.review(coast_id="C1", zones=[_obs(
            density_pressure=0.05, sun_intensity=0.05,
        )])
        assert rep.scores[0].overall > 0.85

    def test_multiple_alerts_overall_drops(
        self, engine: CoastSafetyEngine,
    ) -> None:
        baseline = engine.review(coast_id="C1", zones=[_obs(
            density_pressure=0.05, sun_intensity=0.05,
        )]).scores[0].overall
        bad = engine.review(coast_id="C1", zones=[_obs(
            density_pressure=0.85,
            sun_intensity=0.85,
            stationary_person_signal=0.85,
            flow_anomaly_signal=0.85,
            slip_risk_signal=0.85,
        )]).scores[0].overall
        # Each bad channel takes a meaningful bite out of overall.
        assert bad < baseline - 0.3


class TestEndpointShape:
    def test_camera_run_with_new_fields(self) -> None:
        from fastapi.testclient import TestClient
        from triage4_coast.ui.dashboard_api import app
        c = TestClient(app)
        r = c.post("/camera/run", json={
            "zone_id": "TEST", "zone_kind": "promenade",
            "density_pressure": 0.3, "in_water_motion": 0.0,
            "sun_intensity": 0.4, "lost_child_flag": False,
            "fall_event_flag": True,
            "stationary_person_signal": 0.0,
            "flow_anomaly_signal": 0.0,
            "slip_risk_signal": 0.0,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["alert_count"] >= 1

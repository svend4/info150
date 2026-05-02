"""External-weather provider + auto-trigger rules."""

from __future__ import annotations

import pytest

from triage4_coast.ui import broadcast, weather


@pytest.fixture(autouse=True)
def isolated_state():
    weather.reset()
    broadcast.reset()
    yield
    weather.reset()
    broadcast.reset()


class TestMockProvider:
    def test_fetch_returns_snapshot(self) -> None:
        p = weather.MockWeatherProvider()
        s = p.fetch(lat=43.7, lon=7.3)
        assert s.provider == "mock"
        assert s.air_temp_c == 24.0
        assert s.location_lat == 43.7

    def test_overrides_propagate(self) -> None:
        p = weather.MockWeatherProvider(uv_index=11.0, lightning_strikes_5min=2)
        s = p.fetch(lat=0, lon=0)
        assert s.uv_index == 11.0
        assert s.lightning_strikes_5min == 2


class TestEvaluate:
    def test_calm_day_no_triggers(self) -> None:
        snap = weather.MockWeatherProvider().fetch(lat=0, lon=0)
        triggers = weather.evaluate(snap)
        assert triggers == []

    def test_high_uv_triggers_shade(self) -> None:
        snap = weather.MockWeatherProvider(uv_index=9.0).fetch(lat=0, lon=0)
        triggers = weather.evaluate(snap)
        kinds = [t.kind for t in triggers]
        assert "shade_advisory" in kinds

    def test_lightning_triggers_two(self) -> None:
        snap = weather.MockWeatherProvider(
            lightning_strikes_5min=1,
        ).fetch(lat=0, lon=0)
        triggers = weather.evaluate(snap)
        kinds = [t.kind for t in triggers]
        assert "lightning" in kinds
        assert "clear_water" in kinds

    def test_high_wind_triggers_clear_water(self) -> None:
        snap = weather.MockWeatherProvider(wind_speed_mps=15.0).fetch(lat=0, lon=0)
        triggers = weather.evaluate(snap)
        kinds = [t.kind for t in triggers]
        assert "clear_water" in kinds

    def test_hot_and_sunny_triggers_general(self) -> None:
        snap = weather.MockWeatherProvider(
            air_temp_c=34.0, uv_index=7.0,
        ).fetch(lat=0, lon=0)
        triggers = weather.evaluate(snap)
        kinds = [t.kind for t in triggers]
        assert "general_announcement" in kinds


class TestActuate:
    def test_actuate_records_to_broadcast(self) -> None:
        snap = weather.MockWeatherProvider(uv_index=10.0).fetch(lat=0, lon=0)
        triggers = weather.evaluate(snap)
        entries = weather.actuate(triggers)
        assert len(entries) == len(triggers)
        log = broadcast.recent()
        assert any(e.kind == "shade_advisory" for e in log)

    def test_no_triggers_no_log(self) -> None:
        snap = weather.MockWeatherProvider().fetch(lat=0, lon=0)
        weather.actuate(weather.evaluate(snap))
        assert broadcast.recent() == []


class TestCache:
    def test_initial_latest_is_none(self) -> None:
        assert weather.latest() is None

    def test_cache_round_trip(self) -> None:
        snap = weather.MockWeatherProvider().fetch(lat=0, lon=0)
        weather.cache_latest(snap)
        assert weather.latest() == snap


class TestDefaultProvider:
    def test_no_key_returns_mock(self, monkeypatch) -> None:
        monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
        p = weather.default_provider()
        assert p.name() == "mock"

    def test_blank_key_returns_mock(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENWEATHER_API_KEY", "   ")
        p = weather.default_provider()
        assert p.name() == "mock"

    def test_set_key_returns_openweather(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENWEATHER_API_KEY", "fake-key")
        p = weather.default_provider()
        assert p.name() == "openweather"


class TestEndpoint:
    def test_initial_snapshot_null(self) -> None:
        from fastapi.testclient import TestClient
        from triage4_coast.ui.dashboard_api import app
        c = TestClient(app)
        r = c.get("/coast/weather")
        assert r.status_code == 200
        assert r.json()["snapshot"] is None

    def test_refresh_with_mock(self, monkeypatch) -> None:
        from fastapi.testclient import TestClient
        from triage4_coast.ui.dashboard_api import app
        # Force mock provider regardless of env.
        monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
        c = TestClient(app)
        r = c.post("/coast/weather/refresh", json={"lat": 43.7, "lon": 7.3})
        assert r.status_code == 200
        body = r.json()
        assert body["provider"] == "mock"
        assert body["snapshot"]["air_temp_c"] == 24.0
        # /coast/weather should now return that snapshot
        r2 = c.get("/coast/weather")
        assert r2.json()["snapshot"]["air_temp_c"] == 24.0

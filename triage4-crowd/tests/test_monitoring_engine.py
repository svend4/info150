"""Tests for VenueMonitorEngine + synthetic venue + demo."""

from __future__ import annotations

import pytest

from triage4_crowd.core.models import ZoneObservation
from triage4_crowd.sim.demo_runner import run_demo
from triage4_crowd.sim.synthetic_venue import (
    demo_venue,
    generate_zone_observation,
)
from triage4_crowd.venue_monitor.crowd_safety_bands import CrowdSafetyBands
from triage4_crowd.venue_monitor.monitoring_engine import VenueMonitorEngine


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        VenueMonitorEngine(weights={
            "pressure": 0, "density": 0, "flow": 0, "medical": 0,
        })


def test_engine_handles_empty_zone_list():
    report = VenueMonitorEngine().review("V", zones=[])
    assert report.scores == []
    assert len(report.alerts) == 1
    assert report.alerts[0].kind == "calibration"


def test_engine_empty_observation_surfaces_calibration_alert():
    zone = ZoneObservation(
        zone_id="z", zone_kind="standing", window_duration_s=60.0,
    )
    report = VenueMonitorEngine().review("V", zones=[zone])
    assert any(a.kind == "calibration" for a in report.alerts)


# ---------------------------------------------------------------------------
# Per-channel alerts
# ---------------------------------------------------------------------------


def test_engine_dense_crowd_fires_density_alert():
    zone = generate_zone_observation(
        zone_id="z", zone_kind="standing",
        density_pressure=0.8, seed=1,
    )
    report = VenueMonitorEngine().review("V", zones=[zone])
    density_alerts = [a for a in report.alerts if a.kind == "density"]
    assert any(a.level in ("watch", "urgent") for a in density_alerts)


def test_engine_flow_compaction_fires_urgent():
    zone = generate_zone_observation(
        zone_id="z", zone_kind="egress",
        flow_compaction=0.95, seed=2,
    )
    report = VenueMonitorEngine().review("V", zones=[zone])
    flow_alerts = [a for a in report.alerts if a.kind == "flow"]
    assert any(a.level == "urgent" for a in flow_alerts)


def test_engine_pressure_elevation_fires_urgent():
    zone = generate_zone_observation(
        zone_id="z", zone_kind="standing",
        pressure_level=0.95, seed=3,
    )
    report = VenueMonitorEngine().review("V", zones=[zone])
    pressure_alerts = [a for a in report.alerts if a.kind == "pressure"]
    assert any(a.level == "urgent" for a in pressure_alerts)


def test_engine_medical_candidate_fires_urgent():
    zone = generate_zone_observation(
        zone_id="z", zone_kind="standing",
        medical_rate=1.0, seed=4,
    )
    report = VenueMonitorEngine().review("V", zones=[zone])
    medical_alerts = [a for a in report.alerts if a.kind == "medical"]
    assert any(a.level == "urgent" for a in medical_alerts)


# ---------------------------------------------------------------------------
# Fusion + overrides
# ---------------------------------------------------------------------------


def test_engine_channel_urgent_forces_overall_urgent():
    # Pressure in urgent band but density / flow / medical
    # fine — mortal-sign override should still pull overall
    # level to urgent.
    zone = generate_zone_observation(
        zone_id="z", zone_kind="standing",
        pressure_level=0.95, seed=5,
    )
    report = VenueMonitorEngine().review("V", zones=[zone])
    assert report.scores[0].alert_level == "urgent"


def test_engine_clean_zone_is_ok():
    zone = generate_zone_observation(
        zone_id="z", zone_kind="concourse", seed=6,
    )
    report = VenueMonitorEngine().review("V", zones=[zone])
    assert report.scores[0].alert_level == "ok"


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        zone = generate_zone_observation(
            zone_id=f"z{seed}", zone_kind="standing",
            density_pressure=0.5, flow_compaction=0.5,
            pressure_level=0.5, medical_rate=0.2,
            seed=seed,
        )
        report = VenueMonitorEngine().review("V", zones=[zone])
        assert 0.0 <= report.scores[0].overall <= 1.0


def test_engine_is_deterministic():
    a = generate_zone_observation(
        zone_id="det", pressure_level=0.5, seed=11,
    )
    b = generate_zone_observation(
        zone_id="det", pressure_level=0.5, seed=11,
    )
    eng = VenueMonitorEngine()
    ra = eng.review("V", [a])
    rb = eng.review("V", [b])
    assert ra.scores[0].overall == rb.scores[0].overall
    assert [al.text for al in ra.alerts] == [al.text for al in rb.alerts]


def test_engine_respects_custom_bands():
    strict = CrowdSafetyBands(
        density_watch=0.95, density_urgent=0.80,
        flow_watch=0.95, flow_urgent=0.80,
        pressure_watch=0.95, pressure_urgent=0.80,
        medical_watch=0.95, medical_urgent=0.80,
        overall_watch=0.95, overall_urgent=0.80,
    )
    zone = generate_zone_observation(
        zone_id="z", zone_kind="standing",
        density_pressure=0.3, seed=12,
    )
    eng_strict = VenueMonitorEngine(bands=strict)
    eng_default = VenueMonitorEngine()
    strict_alerts = eng_strict.review("V", [zone]).alerts
    default_alerts = eng_default.review("V", [zone]).alerts
    assert len(strict_alerts) >= len(default_alerts)


# ---------------------------------------------------------------------------
# Synthetic venue + demo runner
# ---------------------------------------------------------------------------


def test_generate_zone_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_zone_observation(density_pressure=2.0)
    with pytest.raises(ValueError):
        generate_zone_observation(flow_compaction=-0.1)
    with pytest.raises(ValueError):
        generate_zone_observation(pressure_level=2.0)
    with pytest.raises(ValueError):
        generate_zone_observation(medical_rate=-0.1)
    with pytest.raises(ValueError):
        generate_zone_observation(window_duration_s=-5)


def test_generate_zone_observation_populates_every_channel():
    zone = generate_zone_observation(seed=13)
    assert len(zone.density_readings) > 0
    assert len(zone.flow_samples) > 0
    assert len(zone.pressure_readings) > 0
    # Medical is optional by construction.


def test_demo_venue_length():
    assert len(demo_venue()) == 5


def test_demo_venue_is_deterministic():
    a = demo_venue()
    b = demo_venue()
    for za, zb in zip(a, b):
        assert [r.persons_per_m2 for r in za.density_readings] == \
               [r.persons_per_m2 for r in zb.density_readings]


def test_run_demo_covers_every_kind_and_level():
    text = run_demo()
    assert "DEMO_VENUE" in text
    for kind in ("density", "flow", "pressure", "medical"):
        assert kind in text
    for level in ("ok", "watch", "urgent"):
        assert level in text


def test_run_demo_survives_six_boundary_claims_guard():
    # Every alert from the engine is emitted through
    # VenueOpsAlert which enforces all six forbidden lists.
    # Demo running cleanly = proof the full guard holds.
    text = run_demo()
    assert "URGENT alerts" in text

"""Tests for DriverMonitoringEngine + synthetic cab."""

from __future__ import annotations

import pytest

from triage4_drive.core.models import DriverObservation
from triage4_drive.driver_monitor.fatigue_bands import FatigueBands
from triage4_drive.driver_monitor.monitoring_engine import (
    DriverMonitoringEngine,
)
from triage4_drive.sim.demo_runner import run_demo
from triage4_drive.sim.synthetic_cab import (
    demo_session,
    generate_observation,
)


# ---------------------------------------------------------------------------
# DriverMonitoringEngine
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        DriverMonitoringEngine(
            weights={"perclos": 0, "distraction": 0, "incapacitation": 0}
        )


def test_engine_alert_channel_for_empty_observation():
    obs = DriverObservation(session_id="s", window_duration_s=5.0)
    score, alerts = DriverMonitoringEngine().review(obs)
    assert score.perclos == 0.0
    assert score.distraction == 0.0
    assert score.incapacitation == 0.0
    # A calibration alert fires on all-empty input.
    assert len(alerts) == 1
    assert alerts[0].kind == "calibration"


def test_engine_alert_driver_gets_ok_level():
    obs = generate_observation(
        session_id="s", drowsiness=0, distraction=0, incapacitation=0,
    )
    score, alerts = DriverMonitoringEngine().review(obs)
    assert score.alert_level == "ok"
    assert alerts == []


def test_engine_drowsy_driver_gets_caution_level():
    obs = generate_observation(
        session_id="s", drowsiness=0.55,
    )
    score, alerts = DriverMonitoringEngine().review(obs, )
    assert score.perclos >= 0.15
    assert any(a.kind == "drowsiness" for a in alerts)


def test_engine_microsleep_forces_critical():
    # High drowsiness → microsleep events guaranteed by the sim.
    obs = generate_observation(
        session_id="s", drowsiness=0.85, seed=42,
    )
    score, alerts = DriverMonitoringEngine().review(obs)
    assert score.alert_level == "critical"
    drowsy = [a for a in alerts if a.kind == "drowsiness"]
    assert any(a.level == "critical" for a in drowsy)


def test_engine_distraction_at_critical_band():
    obs = generate_observation(
        session_id="s", distraction=0.7,
    )
    score, alerts = DriverMonitoringEngine().review(obs)
    assert score.distraction >= 0.5
    assert any(
        a.kind == "distraction" and a.level == "critical" for a in alerts
    )


def test_engine_incapacitation_forces_critical_overall():
    obs = generate_observation(
        session_id="s", incapacitation=0.95,
    )
    score, alerts = DriverMonitoringEngine().review(obs)
    assert score.incapacitation >= 0.9
    # Mortal-sign override: overall floored at 0.9.
    assert score.overall >= 0.9
    assert score.alert_level == "critical"
    incap_alerts = [a for a in alerts if a.kind == "incapacitation"]
    assert any(a.level == "critical" for a in incap_alerts)


def test_engine_is_deterministic():
    obs_a = generate_observation(
        session_id="det", drowsiness=0.6, distraction=0.3, seed=7,
    )
    obs_b = generate_observation(
        session_id="det", drowsiness=0.6, distraction=0.3, seed=7,
    )
    engine = DriverMonitoringEngine()
    sa, aa = engine.review(obs_a)
    sb, ab = engine.review(obs_b)
    assert sa.overall == sb.overall
    assert [a.text for a in aa] == [a.text for a in ab]


def test_engine_respects_custom_bands():
    # Tight bands → alert fires at lower PERCLOS.
    strict = FatigueBands(
        perclos_caution=0.05, perclos_critical=0.15,
        distraction_caution=0.1, distraction_critical=0.3,
        incapacitation_caution=0.3, incapacitation_critical=0.7,
        overall_caution=0.1, overall_critical=0.3,
    )
    obs = generate_observation(
        session_id="s", drowsiness=0.3, seed=1,
    )
    score_strict, alerts_strict = DriverMonitoringEngine(bands=strict).review(obs)
    # Default bands — same input, softer response.
    score_default, alerts_default = DriverMonitoringEngine().review(obs)
    # Strict engine surfaces more alerts for the same input.
    assert len(alerts_strict) >= len(alerts_default)


def test_engine_custom_weights_shift_overall():
    obs = generate_observation(
        session_id="s", drowsiness=0.0, distraction=0.7, seed=1,
    )
    default_overall = DriverMonitoringEngine().review(obs)[0].overall
    # Weight entirely on distraction → overall should go up.
    distraction_only = DriverMonitoringEngine(weights={
        "perclos": 0.0,
        "distraction": 1.0,
        "incapacitation": 0.0,
    }).review(obs)[0].overall
    assert distraction_only > default_overall


# ---------------------------------------------------------------------------
# Synthetic cab + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(drowsiness=2.0)
    with pytest.raises(ValueError):
        generate_observation(distraction=-0.1)
    with pytest.raises(ValueError):
        generate_observation(incapacitation=2.0)
    with pytest.raises(ValueError):
        generate_observation(window_duration_s=-1)
    with pytest.raises(ValueError):
        generate_observation(sample_rate_hz=0)


def test_generate_observation_produces_chronological_samples():
    obs = generate_observation(session_id="s", drowsiness=0.5, seed=3)
    times = [e.t_s for e in obs.eye_samples]
    assert times == sorted(times)


def test_demo_session_has_five_windows():
    windows = demo_session(session_id="X")
    assert len(windows) == 5


def test_demo_session_is_deterministic():
    a = demo_session(session_id="D", seed=2)
    b = demo_session(session_id="D", seed=2)
    # Same eye-sample closures should match frame-by-frame.
    for oa, ob in zip(a, b):
        assert [e.closure for e in oa.eye_samples] == \
               [e.closure for e in ob.eye_samples]


def test_run_demo_covers_every_alert_band():
    text = run_demo()
    assert "DEMO_SESSION" in text
    # Every alert-level label should appear at least once.
    assert "ok" in text
    assert "caution" in text
    assert "critical" in text
    # Every alert kind (except calibration) should appear in
    # the demo at some point.
    assert "drowsiness" in text
    assert "distraction" in text
    assert "incapacitation" in text


def test_run_demo_cues_survive_triple_claims_guard():
    # If the engine ever emits a forbidden clinical /
    # operational / privacy token, DispatcherAlert's
    # constructor throws — so the demo running cleanly is
    # end-to-end proof the triple guard holds.
    text = run_demo()
    assert "CRITICAL alerts" in text

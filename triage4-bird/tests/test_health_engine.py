"""Tests for AvianHealthEngine + synthetic station + demo."""

from __future__ import annotations

import pytest

from triage4_bird.bird_health.monitoring_engine import AvianHealthEngine
from triage4_bird.bird_health.species_acoustic_bands import band_for
from triage4_bird.core.enums import MAX_AVIAN_SMS_CHARS
from triage4_bird.core.models import BirdObservation
from triage4_bird.sim.demo_runner import run_demo
from triage4_bird.sim.synthetic_station import (
    demo_observations,
    generate_observation,
)


# ---------------------------------------------------------------------------
# Species acoustic bands
# ---------------------------------------------------------------------------


def test_band_for_robin():
    b = band_for("robin")
    assert b.species == "robin"
    assert b.wingbeat_low_hz < b.wingbeat_high_hz


def test_band_for_unknown_species():
    """Unknown is a valid enum value; the consumer app uses
    it when classification confidence is low."""
    b = band_for("unknown")
    assert b.species == "unknown"


def test_band_for_bad_name_raises():
    with pytest.raises(KeyError):
        band_for("penguin")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        AvianHealthEngine(weights={
            "call_presence": 0, "distress": 0,
            "vitals": 0, "thermal": 0, "mortality_cluster": 0,
        })


def test_engine_empty_observation_returns_neutral():
    obs = BirdObservation(
        obs_token="O", station_id="A",
        location_handle="grid-1", window_duration_s=60.0,
    )
    report = AvianHealthEngine().review(obs)
    assert len(report.scores) == 1
    assert report.scores[0].overall == 1.0


# ---------------------------------------------------------------------------
# Per-channel escalation
# ---------------------------------------------------------------------------


def test_engine_distress_fraction_escalates():
    obs = generate_observation(
        obs_token="O", station_id="A",
        distress_fraction=0.50, seed=1,
    )
    report = AvianHealthEngine().review(obs)
    distress_alerts = [a for a in report.alerts if a.kind == "distress"]
    assert any(a.level == "urgent" for a in distress_alerts)


def test_engine_wingbeat_anomaly_escalates():
    obs = generate_observation(
        obs_token="O", station_id="A",
        wingbeat_anomaly=0.85, seed=2,
    )
    report = AvianHealthEngine().review(obs)
    vitals_alerts = [a for a in report.alerts if a.kind == "vitals"]
    assert any(a.level == "urgent" for a in vitals_alerts)


def test_engine_call_presence_low_escalates_at_least_to_watch():
    obs = generate_observation(
        obs_token="O", station_id="A",
        expected_species_present_fraction=0.0, seed=3,
    )
    report = AvianHealthEngine().review(obs)
    call_alerts = [a for a in report.alerts if a.kind == "call_presence"]
    assert call_alerts


# ---------------------------------------------------------------------------
# Surveillance-overreach safety — combined alert framing
# ---------------------------------------------------------------------------


def test_engine_thermal_plus_mortality_combined_alert():
    """When both channels are urgent, the engine emits a
    SINGLE combined 'mortality_cluster' alert with the
    'candidate mortality cluster — sampling recommended'
    framing — never an 'outbreak' wording."""
    obs = generate_observation(
        obs_token="O", station_id="D",
        thermal_elevation=0.85,
        dead_bird_count=8,
        seed=4,
    )
    report = AvianHealthEngine().review(obs)
    mortality_alerts = [
        a for a in report.alerts if a.kind == "mortality_cluster"
    ]
    thermal_alerts = [a for a in report.alerts if a.kind == "thermal"]
    # Combined alert: mortality_cluster fires; thermal does NOT
    # also fire as a separate alert.
    assert len(mortality_alerts) == 1
    assert mortality_alerts[0].level == "urgent"
    assert "candidate mortality cluster" in mortality_alerts[0].text
    assert "sampling recommended" in mortality_alerts[0].text
    assert thermal_alerts == []


def test_engine_thermal_only_fires_thermal_alert():
    obs = generate_observation(
        obs_token="O", station_id="A",
        thermal_elevation=0.85, dead_bird_count=0, seed=5,
    )
    report = AvianHealthEngine().review(obs)
    thermal_alerts = [a for a in report.alerts if a.kind == "thermal"]
    mortality_alerts = [
        a for a in report.alerts if a.kind == "mortality_cluster"
    ]
    assert thermal_alerts
    assert mortality_alerts == []


def test_engine_mortality_only_fires_mortality_alert():
    obs = generate_observation(
        obs_token="O", station_id="A",
        thermal_elevation=0.0, dead_bird_count=8, seed=6,
    )
    report = AvianHealthEngine().review(obs)
    mortality_alerts = [
        a for a in report.alerts if a.kind == "mortality_cluster"
    ]
    assert mortality_alerts
    assert mortality_alerts[0].level == "urgent"


# ---------------------------------------------------------------------------
# Determinism + invariants
# ---------------------------------------------------------------------------


def test_engine_is_deterministic():
    a = generate_observation(
        obs_token="det", station_id="A",
        distress_fraction=0.4, seed=11,
    )
    b = generate_observation(
        obs_token="det", station_id="A",
        distress_fraction=0.4, seed=11,
    )
    engine = AvianHealthEngine()
    ra = engine.review(a)
    rb = engine.review(b)
    assert ra.scores[0].overall == rb.scores[0].overall
    assert [al.text for al in ra.alerts] == [al.text for al in rb.alerts]


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        obs = generate_observation(
            obs_token=f"O{seed}", station_id="A",
            distress_fraction=0.3, wingbeat_anomaly=0.3,
            thermal_elevation=0.3, dead_bird_count=2,
            seed=seed,
        )
        report = AvianHealthEngine().review(obs)
        assert 0.0 <= report.scores[0].overall <= 1.0


def test_engine_every_alert_fits_sms_budget():
    for obs in demo_observations():
        report = AvianHealthEngine().review(obs)
        for alert in report.alerts:
            assert len(alert.text) <= MAX_AVIAN_SMS_CHARS


def test_engine_alert_handles_match_observation_handle():
    for obs in demo_observations():
        report = AvianHealthEngine().review(obs)
        for alert in report.alerts:
            assert alert.location_handle == obs.location_handle


# ---------------------------------------------------------------------------
# Synthetic station + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(distress_fraction=2.0)
    with pytest.raises(ValueError):
        generate_observation(wingbeat_anomaly=-0.1)
    with pytest.raises(ValueError):
        generate_observation(thermal_elevation=2.0)
    with pytest.raises(ValueError):
        generate_observation(dead_bird_count=-1)
    with pytest.raises(ValueError):
        generate_observation(window_duration_s=-5)


def test_demo_observations_length():
    assert len(demo_observations()) == 5


def test_demo_observations_deterministic():
    a = demo_observations()
    b = demo_observations()
    for oa, ob in zip(a, b):
        assert [c.species for c in oa.call_samples] == \
               [c.species for c in ob.call_samples]


def test_run_demo_covers_every_alert_level():
    text = run_demo()
    for level in ("ok", "watch", "urgent"):
        assert level in text


def test_run_demo_survives_full_claims_guard():
    text = run_demo()
    assert "URGENT" in text


# ---------------------------------------------------------------------------
# Property tests on demo output
# ---------------------------------------------------------------------------


def test_run_demo_never_mentions_avian_flu_or_outbreak():
    """Property test: the demo output never contains
    surveillance-overreach vocabulary, even though one of
    the demo observations specifically triggers the
    thermal+mortality combined alert. The library's
    architecture forces 'candidate mortality cluster —
    sampling recommended' framing instead."""
    text = run_demo().lower()
    for phrase in (
        "avian flu",
        "hpai",
        "outbreak",
        "epidemic",
        "pandemic",
        "h5n1",
        "h7n9",
        "h5n8",
        "flu strain",
    ):
        assert phrase not in text


def test_run_demo_never_echoes_voice_content():
    """Audio-privacy property: demo output never contains
    voice-quoting vocabulary."""
    text = run_demo().lower()
    for phrase in (
        "person said",
        "someone said",
        "voice content",
        "conversation captured",
        "human speech",
        "audio of speaker",
        "transcribed audio",
    ):
        assert phrase not in text


def test_run_demo_uses_sampling_recommended_framing():
    """Property: when the demo's mortality cluster fires,
    the alert text uses the surveillance-overreach-safe
    'candidate mortality cluster — sampling recommended'
    wording."""
    text = run_demo()
    assert "candidate mortality cluster" in text
    assert "sampling recommended" in text


def test_run_demo_never_emits_decimal_coords():
    import re
    text = run_demo()
    assert not re.search(
        r"[-+]?\d+\.\d{2,}\s*[,\s]\s*[-+]?\d+\.\d{2,}", text,
    )

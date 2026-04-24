"""Tests for SiteSafetyEngine + synthetic shift + demo."""

from __future__ import annotations

import pytest

from triage4_site.core.models import WorkerObservation
from triage4_site.sim.demo_runner import run_demo
from triage4_site.sim.synthetic_shift import demo_shift, generate_observation
from triage4_site.site_monitor.monitoring_engine import SiteSafetyEngine
from triage4_site.site_monitor.safety_bands import SafetyBands


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        SiteSafetyEngine(weights={
            "ppe": 0, "lifting": 0, "heat": 0, "fatigue": 0,
        })


def test_engine_handles_empty_observation_list():
    report = SiteSafetyEngine().review(site_id="S", observations=[])
    assert report.scores == []
    assert len(report.alerts) == 1
    assert report.alerts[0].kind == "calibration"


def test_engine_empty_observation_surfaces_calibration_alert():
    obs = WorkerObservation(worker_token="w", window_duration_s=60.0)
    report = SiteSafetyEngine().review(site_id="S", observations=[obs])
    assert any(a.kind == "calibration" for a in report.alerts)


# ---------------------------------------------------------------------------
# Per-channel alerts
# ---------------------------------------------------------------------------


def test_engine_ppe_gap_fires_alert():
    obs = generate_observation(
        worker_token="w", ppe_compliance=0.7, seed=1,
    )
    report = SiteSafetyEngine().review(site_id="S", observations=[obs])
    ppe_alerts = [a for a in report.alerts if a.kind == "ppe"]
    assert any(a.level in ("watch", "urgent") for a in ppe_alerts)


def test_engine_ppe_no_alert_when_no_required():
    obs = generate_observation(
        worker_token="w", required_ppe=(), ppe_compliance=0.0, seed=1,
    )
    report = SiteSafetyEngine().review(site_id="S", observations=[obs])
    ppe_alerts = [a for a in report.alerts if a.kind == "ppe"]
    assert ppe_alerts == []


def test_engine_unsafe_lifting_fires_urgent():
    obs = generate_observation(
        worker_token="w", unsafe_lifting=0.9, seed=2,
    )
    report = SiteSafetyEngine().review(site_id="S", observations=[obs])
    lifting_alerts = [a for a in report.alerts if a.kind == "lifting"]
    assert any(a.level == "urgent" for a in lifting_alerts)


def test_engine_heat_stress_fires_urgent():
    obs = generate_observation(
        worker_token="w", heat_stress=0.9, seed=3,
    )
    report = SiteSafetyEngine().review(site_id="S", observations=[obs])
    heat_alerts = [a for a in report.alerts if a.kind == "heat"]
    assert any(a.level == "urgent" for a in heat_alerts)


def test_engine_fatigue_fires_urgent():
    obs = generate_observation(
        worker_token="w", fatigue=0.9, seed=4,
    )
    report = SiteSafetyEngine().review(site_id="S", observations=[obs])
    fatigue_alerts = [a for a in report.alerts if a.kind == "fatigue"]
    assert any(a.level == "urgent" for a in fatigue_alerts)


# ---------------------------------------------------------------------------
# Fusion + overrides
# ---------------------------------------------------------------------------


def test_engine_channel_urgent_forces_overall_urgent():
    # Lifting in urgent band but other channels fine — the
    # mortal-sign override should still pull overall level
    # to urgent.
    obs = generate_observation(
        worker_token="w", unsafe_lifting=0.9, seed=5,
    )
    report = SiteSafetyEngine().review(site_id="S", observations=[obs])
    assert report.scores[0].alert_level == "urgent"


def test_engine_clean_observation_is_ok():
    obs = generate_observation(worker_token="w", seed=6)
    report = SiteSafetyEngine().review(site_id="S", observations=[obs])
    assert report.scores[0].alert_level == "ok"


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        obs = generate_observation(
            worker_token=f"w{seed}",
            ppe_compliance=0.5, unsafe_lifting=0.5,
            heat_stress=0.5, fatigue=0.5,
            seed=seed,
        )
        report = SiteSafetyEngine().review(site_id="S", observations=[obs])
        assert 0.0 <= report.scores[0].overall <= 1.0


def test_engine_site_condition_dusty_lowers_ppe_influence():
    # Moderate PPE gap (watch band, not urgent) so the
    # mortal-sign override doesn't kick in and we can observe
    # the confidence-weighting effect on the fused overall.
    obs_clear = generate_observation(
        worker_token="w", ppe_compliance=0.70,
        site_condition="clear", seed=7,
    )
    obs_dusty = generate_observation(
        worker_token="w", ppe_compliance=0.70,
        site_condition="dusty", seed=7,
    )
    eng = SiteSafetyEngine()
    overall_clear = eng.review("S", [obs_clear]).scores[0].overall
    overall_dusty = eng.review("S", [obs_dusty]).scores[0].overall
    # Under dusty conditions the fused overall should be
    # HIGHER (less penalised) because PPE confidence drops
    # and the engine blends the channel toward a neutral 1.0.
    assert overall_dusty > overall_clear


def test_engine_is_deterministic():
    obs_a = generate_observation(
        worker_token="det", unsafe_lifting=0.5, seed=11,
    )
    obs_b = generate_observation(
        worker_token="det", unsafe_lifting=0.5, seed=11,
    )
    eng = SiteSafetyEngine()
    ra = eng.review("S", [obs_a])
    rb = eng.review("S", [obs_b])
    assert ra.scores[0].overall == rb.scores[0].overall
    assert [a.text for a in ra.alerts] == [a.text for a in rb.alerts]


def test_engine_respects_custom_bands():
    # Strict bands should fire more alerts for the same input.
    strict = SafetyBands(
        ppe_watch=0.95, ppe_urgent=0.80,
        lifting_watch=0.90, lifting_urgent=0.70,
        heat_watch=0.90, heat_urgent=0.70,
        fatigue_watch=0.90, fatigue_urgent=0.70,
        overall_watch=0.95, overall_urgent=0.70,
    )
    obs = generate_observation(
        worker_token="w", ppe_compliance=0.9, seed=12,
    )
    eng_strict = SiteSafetyEngine(bands=strict)
    eng_default = SiteSafetyEngine()
    strict_alerts = eng_strict.review("S", [obs]).alerts
    default_alerts = eng_default.review("S", [obs]).alerts
    assert len(strict_alerts) >= len(default_alerts)


# ---------------------------------------------------------------------------
# Synthetic shift + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(ppe_compliance=2.0)
    with pytest.raises(ValueError):
        generate_observation(unsafe_lifting=-0.1)
    with pytest.raises(ValueError):
        generate_observation(heat_stress=2.0)
    with pytest.raises(ValueError):
        generate_observation(fatigue=-0.1)
    with pytest.raises(ValueError):
        generate_observation(window_duration_s=-5)


def test_generate_observation_has_samples_on_every_channel():
    obs = generate_observation(seed=13)
    assert len(obs.ppe_samples) > 0
    assert len(obs.lifting_samples) > 0
    assert len(obs.thermal_samples) > 0
    assert len(obs.gait_samples) > 0


def test_demo_shift_length():
    assert len(demo_shift()) == 5


def test_demo_shift_is_deterministic():
    a = demo_shift()
    b = demo_shift()
    for oa, ob in zip(a, b):
        assert [p.items_detected for p in oa.ppe_samples] == \
               [p.items_detected for p in ob.ppe_samples]


def test_run_demo_covers_every_alert_kind_and_level():
    text = run_demo()
    assert "DEMO_SITE" in text
    for kind in ("ppe", "lifting", "heat", "fatigue"):
        assert kind in text
    for level in ("ok", "watch", "urgent"):
        assert level in text


def test_run_demo_survives_five_boundary_claims_guard():
    # Any forbidden token would throw at alert construction
    # time; demo running cleanly = proof the full guard holds.
    text = run_demo()
    assert "URGENT alerts" in text

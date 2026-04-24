"""Tests for HomeMonitoringEngine + synthetic day + demo."""

from __future__ import annotations

import pytest

from triage4_home.core.models import (
    ImpactSample,
    ResidentObservation,
)
from triage4_home.home_monitor.fall_thresholds import FallThresholds
from triage4_home.home_monitor.monitoring_engine import (
    HomeMonitoringEngine,
    ResidentBaseline,
)
from triage4_home.signatures.activity_pattern import ActivityFractions
from triage4_home.sim.demo_runner import run_demo
from triage4_home.sim.synthetic_day import (
    demo_baseline,
    demo_day_series,
    generate_observation,
)


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        HomeMonitoringEngine(
            weights={"fall": 0, "activity": 0, "mobility": 0}
        )


def test_engine_empty_observation_surfaces_baseline_alert():
    obs = ResidentObservation(window_id="w", window_duration_s=60.0)
    score, alerts = HomeMonitoringEngine().review(obs)
    # All-empty input surfaces a baseline alert.
    assert any(a.kind == "baseline" for a in alerts)
    # Score channels all neutral.
    assert 0.0 <= score.overall <= 1.0


# ---------------------------------------------------------------------------
# Fall channel
# ---------------------------------------------------------------------------


def test_engine_fall_candidate_forces_urgent():
    obs = generate_observation(
        window_id="w", fall_event=True, seed=1,
    )
    score, alerts = HomeMonitoringEngine().review(
        obs, baseline=demo_baseline(),
    )
    assert score.fall_risk == 1.0
    assert score.alert_level == "urgent"
    fall_alerts = [a for a in alerts if a.kind == "fall"]
    assert any(a.level == "urgent" for a in fall_alerts)


def test_engine_fall_candidate_overrides_good_other_channels():
    obs = ResidentObservation(
        window_id="w", window_duration_s=3600.0,
        impacts=[ImpactSample(t_s=100, magnitude_g=3.5, stillness_after_s=15.0)],
    )
    score, alerts = HomeMonitoringEngine().review(obs)
    # Even with no activity / mobility data, a candidate fall
    # dominates and the level goes to urgent.
    assert score.alert_level == "urgent"
    assert any(a.kind == "fall" and a.level == "urgent" for a in alerts)


def test_engine_borderline_fall_fires_check_in():
    obs = ResidentObservation(
        window_id="w", window_duration_s=3600.0,
        impacts=[ImpactSample(t_s=100, magnitude_g=2.5, stillness_after_s=2.0)],
    )
    _, alerts = HomeMonitoringEngine().review(obs)
    fall_alerts = [a for a in alerts if a.kind == "fall"]
    assert any(a.level == "check_in" for a in fall_alerts)


# ---------------------------------------------------------------------------
# Activity channel
# ---------------------------------------------------------------------------


def test_engine_activity_alignment_without_baseline_surfaces_pending_cue():
    obs = generate_observation(window_id="w", seed=1)
    _, alerts = HomeMonitoringEngine().review(obs, baseline=None)
    baseline_alerts = [a for a in alerts if a.kind == "baseline"]
    assert any("baseline not yet established" in a.text
               for a in baseline_alerts)


def test_engine_strong_activity_deviation_fires_check_in():
    obs = generate_observation(
        window_id="w", activity_deviation=0.9, seed=1,
    )
    _, alerts = HomeMonitoringEngine().review(
        obs, baseline=demo_baseline(),
    )
    activity_alerts = [a for a in alerts if a.kind == "activity"]
    assert any(a.level in ("check_in", "urgent") for a in activity_alerts)


# ---------------------------------------------------------------------------
# Mobility channel
# ---------------------------------------------------------------------------


def test_engine_mobility_decline_fires_alert():
    obs = generate_observation(
        window_id="w", mobility_decline=0.5, seed=1,
    )
    _, alerts = HomeMonitoringEngine().review(
        obs, baseline=demo_baseline(),
    )
    mobility_alerts = [a for a in alerts if a.kind == "mobility"]
    assert any(a.level in ("check_in", "urgent") for a in mobility_alerts)


def test_engine_no_mobility_alert_without_baseline():
    # Without a baseline, mobility cannot be judged as a
    # decline — no mobility-specific alert should fire.
    obs = generate_observation(window_id="w", mobility_decline=0.8, seed=1)
    _, alerts = HomeMonitoringEngine().review(obs, baseline=None)
    mobility_alerts = [a for a in alerts if a.kind == "mobility"]
    assert mobility_alerts == []


# ---------------------------------------------------------------------------
# Fusion + determinism
# ---------------------------------------------------------------------------


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        obs = generate_observation(
            window_id=f"w{seed}",
            activity_deviation=0.3,
            mobility_decline=0.3,
            seed=seed,
        )
        score, _ = HomeMonitoringEngine().review(
            obs, baseline=demo_baseline(),
        )
        assert 0.0 <= score.overall <= 1.0


def test_engine_is_deterministic():
    obs_a = generate_observation(
        window_id="w", activity_deviation=0.5, seed=7,
    )
    obs_b = generate_observation(
        window_id="w", activity_deviation=0.5, seed=7,
    )
    baseline = demo_baseline()
    engine = HomeMonitoringEngine()
    sa, aa = engine.review(obs_a, baseline=baseline)
    sb, ab = engine.review(obs_b, baseline=baseline)
    assert sa.overall == sb.overall
    assert [a.text for a in aa] == [a.text for a in ab]


def test_engine_respects_custom_thresholds():
    # Tighter impact threshold → 2.5 g impact now triggers
    # a candidate instead of borderline.
    strict = FallThresholds(
        impact_threshold_g=1.5, impact_high_g=2.5,
        stillness_threshold_s=1.0,
    )
    obs = ResidentObservation(
        window_id="w", window_duration_s=3600.0,
        impacts=[ImpactSample(t_s=100, magnitude_g=2.0, stillness_after_s=2.0)],
    )
    _, alerts_strict = HomeMonitoringEngine(thresholds=strict).review(obs)
    _, alerts_default = HomeMonitoringEngine().review(obs)
    # Strict engine classifies this as candidate → urgent
    # fall alert. Default engine classifies as none or
    # borderline.
    assert any(a.kind == "fall" and a.level == "urgent"
               for a in alerts_strict)
    assert not any(a.kind == "fall" and a.level == "urgent"
                   for a in alerts_default)


# ---------------------------------------------------------------------------
# Synthetic day + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(activity_deviation=2.0)
    with pytest.raises(ValueError):
        generate_observation(mobility_decline=-0.1)
    with pytest.raises(ValueError):
        generate_observation(window_duration_s=-1)


def test_generate_observation_has_transitions():
    obs = generate_observation(window_id="w", seed=0)
    assert len(obs.transitions) >= 5


def test_demo_day_series_length():
    series = demo_day_series()
    assert len(series) == 5


def test_demo_day_series_is_deterministic():
    a = demo_day_series()
    b = demo_day_series()
    # Same day_id in both — activity samples should match
    # intensity-for-intensity.
    for oa, ob in zip(a, b):
        assert [s.intensity for s in oa.activity_samples] == \
               [s.intensity for s in ob.activity_samples]


def test_demo_baseline_matches_fractions_shape():
    b = demo_baseline()
    assert isinstance(b, ResidentBaseline)
    assert b.activity is not None
    assert isinstance(b.activity, ActivityFractions)
    assert b.mobility_median_mps is not None


def test_run_demo_covers_every_alert_level():
    text = run_demo()
    assert "DEMO_RESIDENCE" in text
    # Every level label should appear somewhere in the demo.
    assert "ok" in text
    assert "check_in" in text
    assert "urgent" in text
    # Every alert kind that the engine uses shows up too.
    assert "fall" in text
    assert "activity" in text
    assert "mobility" in text


def test_run_demo_survives_quadruple_claims_guard():
    # Any forbidden clinical / operational / privacy /
    # dignity token inside an emitted cue would throw during
    # construction, so the demo running cleanly is end-to-end
    # proof that all four guards hold.
    text = run_demo()
    assert "URGENT alerts" in text

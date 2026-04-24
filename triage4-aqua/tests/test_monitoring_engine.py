"""Tests for PoolWatchEngine + synthetic pool + demo."""

from __future__ import annotations

import pytest

from triage4_aqua.core.models import SwimmerObservation
from triage4_aqua.pool_watch.drowning_bands import DrowningBands
from triage4_aqua.pool_watch.monitoring_engine import PoolWatchEngine
from triage4_aqua.sim.demo_runner import run_demo
from triage4_aqua.sim.synthetic_pool import demo_pool, generate_observation


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        PoolWatchEngine(weights={
            "submersion": 0, "idr": 0, "absent": 0, "distress": 0,
        })


def test_engine_handles_empty_observation_list():
    report = PoolWatchEngine().review("P", observations=[])
    assert report.scores == []
    assert len(report.alerts) == 1
    assert report.alerts[0].kind == "calibration"


def test_engine_empty_observation_surfaces_calibration_alert():
    obs = SwimmerObservation(
        swimmer_token="s", zone="pool", window_duration_s=30.0,
    )
    report = PoolWatchEngine().review("P", observations=[obs])
    assert any(a.kind == "calibration" for a in report.alerts)


# ---------------------------------------------------------------------------
# Per-channel alerts
# ---------------------------------------------------------------------------


def test_engine_submersion_urgent_fires():
    obs = generate_observation(
        swimmer_token="s", submersion_s=40.0, seed=1,
    )
    report = PoolWatchEngine().review("P", observations=[obs])
    sub_alerts = [a for a in report.alerts if a.kind == "submersion"]
    assert any(a.level == "urgent" for a in sub_alerts)


def test_engine_submersion_watch_fires():
    obs = generate_observation(
        swimmer_token="s", submersion_s=22.0, seed=1,
    )
    report = PoolWatchEngine().review("P", observations=[obs])
    sub_alerts = [a for a in report.alerts if a.kind == "submersion"]
    assert any(a.level == "watch" for a in sub_alerts)


def test_engine_idr_urgent_fires():
    obs = generate_observation(
        swimmer_token="s", idr_severity=0.9, seed=1,
    )
    report = PoolWatchEngine().review("P", observations=[obs])
    idr_alerts = [a for a in report.alerts if a.kind == "idr"]
    assert any(a.level == "urgent" for a in idr_alerts)


def test_engine_absence_urgent_fires():
    obs = generate_observation(
        swimmer_token="s", absence_s=50.0, seed=1,
    )
    report = PoolWatchEngine().review("P", observations=[obs])
    absent_alerts = [a for a in report.alerts if a.kind == "absent"]
    assert any(a.level == "urgent" for a in absent_alerts)


def test_engine_distress_urgent_fires():
    obs = generate_observation(
        swimmer_token="s", distress_level=0.8, seed=1,
    )
    report = PoolWatchEngine().review("P", observations=[obs])
    distress_alerts = [a for a in report.alerts if a.kind == "distress"]
    assert any(a.level == "urgent" for a in distress_alerts)


# ---------------------------------------------------------------------------
# Fusion + overrides
# ---------------------------------------------------------------------------


def test_engine_channel_urgent_forces_overall_urgent():
    # Submersion in urgent band — other channels should NOT
    # mask this.
    obs = generate_observation(
        swimmer_token="s", submersion_s=40.0, seed=2,
    )
    report = PoolWatchEngine().review("P", observations=[obs])
    assert report.scores[0].alert_level == "urgent"


def test_engine_clean_swimmer_is_ok():
    obs = generate_observation(swimmer_token="s", seed=3)
    report = PoolWatchEngine().review("P", observations=[obs])
    assert report.scores[0].alert_level == "ok"


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        obs = generate_observation(
            swimmer_token=f"s{seed}",
            submersion_s=10.0, idr_severity=0.3,
            absence_s=15.0, distress_level=0.3,
            seed=seed,
        )
        report = PoolWatchEngine().review("P", observations=[obs])
        assert 0.0 <= report.scores[0].overall <= 1.0


def test_engine_pool_condition_turbid_lowers_visible_channels():
    # Same mild IDR severity (watch band, not urgent) so the
    # channel-urgent mortal-sign override doesn't floor both
    # cases to the same value. Under turbid water the fused
    # overall should be HIGHER (less penalised) because
    # visible-light channels are blended toward neutral.
    obs_clear = generate_observation(
        swimmer_token="s", idr_severity=0.15,
        pool_condition="clear", seed=7,
    )
    obs_turbid = generate_observation(
        swimmer_token="s", idr_severity=0.15,
        pool_condition="turbid", seed=7,
    )
    eng = PoolWatchEngine()
    clear_overall = eng.review("P", [obs_clear]).scores[0].overall
    turbid_overall = eng.review("P", [obs_turbid]).scores[0].overall
    assert turbid_overall > clear_overall


def test_engine_is_deterministic():
    a = generate_observation(
        swimmer_token="det", submersion_s=20.0, seed=11,
    )
    b = generate_observation(
        swimmer_token="det", submersion_s=20.0, seed=11,
    )
    eng = PoolWatchEngine()
    ra = eng.review("P", [a])
    rb = eng.review("P", [b])
    assert ra.scores[0].overall == rb.scores[0].overall
    assert [al.text for al in ra.alerts] == [al.text for al in rb.alerts]


def test_engine_respects_custom_bands():
    strict = DrowningBands(
        submersion_watch=0.95, submersion_urgent=0.80,
        idr_watch=0.95, idr_urgent=0.80,
        absent_watch=0.95, absent_urgent=0.80,
        distress_watch=0.95, distress_urgent=0.80,
        overall_watch=0.95, overall_urgent=0.80,
        submersion_watch_s=5.0, submersion_urgent_s=10.0,
    )
    obs = generate_observation(
        swimmer_token="s", submersion_s=7.0, seed=12,
    )
    eng_strict = PoolWatchEngine(bands=strict)
    eng_default = PoolWatchEngine()
    strict_alerts = eng_strict.review("P", [obs]).alerts
    default_alerts = eng_default.review("P", [obs]).alerts
    assert len(strict_alerts) >= len(default_alerts)


# ---------------------------------------------------------------------------
# Synthetic pool + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(idr_severity=2.0)
    with pytest.raises(ValueError):
        generate_observation(distress_level=-0.1)
    with pytest.raises(ValueError):
        generate_observation(submersion_s=-1)
    with pytest.raises(ValueError):
        generate_observation(absence_s=-1)
    with pytest.raises(ValueError):
        generate_observation(window_duration_s=-5)


def test_demo_pool_length():
    assert len(demo_pool()) == 5


def test_demo_pool_is_deterministic():
    a = demo_pool()
    b = demo_pool()
    for oa, ob in zip(a, b):
        assert [s.submerged for s in oa.submersion_samples] == \
               [s.submerged for s in ob.submersion_samples]


def test_run_demo_covers_every_kind_and_level():
    text = run_demo()
    assert "DEMO_POOL" in text
    for kind in ("submersion", "idr", "absent", "distress"):
        assert kind in text
    for level in ("ok", "watch", "urgent"):
        assert level in text


def test_run_demo_survives_seven_boundary_claims_guard():
    # Any forbidden token (clinical / operational / privacy /
    # dignity / labor / panic / no-false-reassurance) would
    # throw at LifeguardAlert construction. Demo running
    # cleanly = proof the full seven-guard holds.
    text = run_demo()
    assert "URGENT alerts" in text


def test_run_demo_never_uses_reassurance_language():
    """Critical property test — the no-false-reassurance
    boundary is architectural. Verify the demo output
    doesn't accidentally contain reassuring phrases
    anywhere, even in summary fields."""
    text = run_demo().lower()
    for phrase in (
        "all clear",
        "pool is safe",
        "no drowning detected",
        "no incidents",
        "all swimmers safe",
        "confirmed safe",
        "nothing to worry about",
        "rest assured",
    ):
        assert phrase not in text

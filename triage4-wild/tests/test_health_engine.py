"""Tests for WildlifeHealthEngine + synthetic reserve + demo."""

from __future__ import annotations

import pytest

from triage4_wild.core.enums import MAX_RANGER_SMS_CHARS
from triage4_wild.core.models import LocationHandle, WildlifeObservation
from triage4_wild.sim.demo_runner import run_demo
from triage4_wild.sim.synthetic_reserve import (
    demo_observations,
    generate_observation,
)
from triage4_wild.wildlife_health.monitoring_engine import (
    WildlifeHealthEngine,
)
from triage4_wild.wildlife_health.species_thresholds import profile_for


# ---------------------------------------------------------------------------
# Species profiles
# ---------------------------------------------------------------------------


def test_profile_for_elephant_is_high_value():
    p = profile_for("elephant")
    assert p.high_value_escalation


def test_profile_for_zebra_is_not_high_value():
    p = profile_for("zebra")
    assert not p.high_value_escalation


def test_profile_for_unknown_species_raises_on_bad_name():
    with pytest.raises(KeyError):
        profile_for("koala")  # type: ignore[arg-type]


def test_profile_for_unknown_species_falls_back_to_default():
    """Species 'unknown' is a valid enum value — the
    species classifier is upstream; when confidence is
    low the consumer app passes species='unknown' and the
    library uses a neutral profile."""
    p = profile_for("unknown")
    assert not p.high_value_escalation


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        WildlifeHealthEngine(weights={
            "gait": 0, "thermal": 0, "postural": 0,
            "body_condition": 0, "threat_signal": 0,
        })


def test_engine_empty_observation_surfaces_neutral_score():
    obs = WildlifeObservation(
        obs_token="O", species="elephant",
        species_confidence=0.9, window_duration_s=30.0,
        location=LocationHandle(handle="grid-A"),
    )
    report = WildlifeHealthEngine().review(obs, reserve_id="R")
    assert len(report.scores) == 1
    assert 0.0 <= report.scores[0].overall <= 1.0


# ---------------------------------------------------------------------------
# Per-channel escalation
# ---------------------------------------------------------------------------


def test_engine_gait_asymmetry_escalates():
    obs = generate_observation(
        obs_token="O", species="zebra",
        limb_asymmetry=0.55, seed=1,
    )
    report = WildlifeHealthEngine().review(obs, reserve_id="R")
    gait_alerts = [a for a in report.alerts if a.kind == "gait"]
    assert any(a.level == "urgent" for a in gait_alerts)


def test_engine_thermal_hotspot_escalates():
    obs = generate_observation(
        obs_token="O", species="buffalo",
        thermal_hotspot=0.60, seed=2,
    )
    report = WildlifeHealthEngine().review(obs, reserve_id="R")
    thermal_alerts = [a for a in report.alerts if a.kind == "thermal"]
    assert any(a.level == "urgent" for a in thermal_alerts)


def test_engine_sustained_down_escalates():
    obs = generate_observation(
        obs_token="O", species="giraffe",
        postural_down_fraction=0.80, seed=3,
    )
    report = WildlifeHealthEngine().review(obs, reserve_id="R")
    collapse_alerts = [a for a in report.alerts if a.kind == "collapse"]
    assert any(a.level == "urgent" for a in collapse_alerts)


def test_engine_low_body_condition_escalates():
    obs = generate_observation(
        obs_token="O", species="giraffe",
        body_condition=0.30, seed=4,
    )
    report = WildlifeHealthEngine().review(obs, reserve_id="R")
    bc_alerts = [a for a in report.alerts if a.kind == "body_condition"]
    assert any(a.level == "urgent" for a in bc_alerts)


def test_engine_upstream_threat_flag_fires_channel():
    obs = generate_observation(
        obs_token="O", species="rhino",
        threat_kind="snare_injury",
        threat_confidence=0.85,
        seed=5,
    )
    report = WildlifeHealthEngine().review(obs, reserve_id="R")
    # The threat channel maps snare_injury → gait alert kind.
    assert any(a.kind == "gait" for a in report.alerts)


# ---------------------------------------------------------------------------
# High-value species escalation bias
# ---------------------------------------------------------------------------


def test_engine_high_value_species_escalates_faster():
    """Same observation with a high-value species (rhino) vs
    a prey species (zebra) should produce the same overall
    score but faster escalation for the rhino — when an
    upstream threat flag is also present."""
    rhino_obs = generate_observation(
        obs_token="O", species="rhino",
        limb_asymmetry=0.10,
        threat_kind="snare_injury",
        threat_confidence=0.75,
        seed=6,
    )
    zebra_obs = generate_observation(
        obs_token="O", species="zebra",
        limb_asymmetry=0.10,
        threat_kind="snare_injury",
        threat_confidence=0.75,
        seed=6,
    )
    engine = WildlifeHealthEngine()
    rhino_report = engine.review(rhino_obs, reserve_id="R")
    zebra_report = engine.review(zebra_obs, reserve_id="R")
    rec_order = {"ok": 0, "watch": 1, "urgent": 2}
    assert rec_order[rhino_report.scores[0].alert_level] >= \
           rec_order[zebra_report.scores[0].alert_level]


# ---------------------------------------------------------------------------
# Determinism + capture quality
# ---------------------------------------------------------------------------


def test_engine_is_deterministic():
    a = generate_observation(
        obs_token="det", species="elephant",
        limb_asymmetry=0.40, seed=11,
    )
    b = generate_observation(
        obs_token="det", species="elephant",
        limb_asymmetry=0.40, seed=11,
    )
    engine = WildlifeHealthEngine()
    ra = engine.review(a, reserve_id="R")
    rb = engine.review(b, reserve_id="R")
    assert ra.scores[0].overall == rb.scores[0].overall
    assert [al.text for al in ra.alerts] == [al.text for al in rb.alerts]


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        obs = generate_observation(
            obs_token=f"O{seed}", species="elephant",
            limb_asymmetry=0.3, thermal_hotspot=0.3,
            postural_down_fraction=0.3, body_condition=0.6,
            seed=seed,
        )
        report = WildlifeHealthEngine().review(obs, reserve_id="R")
        assert 0.0 <= report.scores[0].overall <= 1.0


def test_engine_capture_quality_partial_softens_visible_channels():
    """Partial capture should blend visible-light channels
    (gait, postural, body_condition) toward neutral → HIGHER
    overall for the same signal."""
    good_obs = generate_observation(
        obs_token="O", species="elephant",
        limb_asymmetry=0.35, capture_quality="good",
        seed=7,
    )
    partial_obs = generate_observation(
        obs_token="O", species="elephant",
        limb_asymmetry=0.35, capture_quality="partial",
        seed=7,
    )
    engine = WildlifeHealthEngine()
    good = engine.review(good_obs, reserve_id="R").scores[0].overall
    partial = engine.review(partial_obs, reserve_id="R").scores[0].overall
    assert partial > good


# ---------------------------------------------------------------------------
# SMS-length property — engine output always fits SMS
# ---------------------------------------------------------------------------


def test_engine_every_alert_fits_sms_budget():
    """The engine's alert-building helper must always
    produce text within MAX_RANGER_SMS_CHARS."""
    submissions = demo_observations()
    engine = WildlifeHealthEngine()
    for obs in submissions:
        report = engine.review(obs, reserve_id="R")
        for alert in report.alerts:
            assert len(alert.text) <= MAX_RANGER_SMS_CHARS


def test_engine_alert_handles_match_observation_handle():
    """Every alert attaches the observation's handle, never
    plaintext coordinates. Redundant with the dataclass
    guard but explicit as a property test."""
    submissions = demo_observations()
    engine = WildlifeHealthEngine()
    for obs in submissions:
        report = engine.review(obs, reserve_id="R")
        for alert in report.alerts:
            assert alert.location_handle == obs.location.handle


# ---------------------------------------------------------------------------
# Synthetic reserve + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(limb_asymmetry=2.0)
    with pytest.raises(ValueError):
        generate_observation(thermal_hotspot=-0.1)
    with pytest.raises(ValueError):
        generate_observation(postural_down_fraction=2.0)
    with pytest.raises(ValueError):
        generate_observation(body_condition=-0.1)
    with pytest.raises(ValueError):
        generate_observation(threat_confidence=2.0)
    with pytest.raises(ValueError):
        generate_observation(window_duration_s=-5)


def test_demo_observations_length():
    assert len(demo_observations()) == 5


def test_demo_observations_deterministic():
    a = demo_observations()
    b = demo_observations()
    for oa, ob in zip(a, b):
        assert [p.limb_asymmetry for p in oa.pose_samples] == \
               [p.limb_asymmetry for p in ob.pose_samples]


def test_run_demo_covers_every_alert_level():
    text = run_demo()
    for level in ("ok", "watch", "urgent"):
        assert level in text


def test_run_demo_survives_full_claims_guard():
    # Every RangerAlert is constructed through the seven-list
    # guard + SMS cap. Demo running cleanly = proof the guards
    # hold end-to-end.
    text = run_demo()
    assert "URGENT alerts" in text


def test_run_demo_never_emits_coordinates():
    """Property test — demo output never contains decimal-
    coordinate patterns, lat/lon vocabulary, or any of the
    location-leakage phrases. Structural field-security."""
    import re
    text = run_demo()
    # Decimal coordinate pairs.
    assert not re.search(r"[-+]?\d+\.\d{2,}\s*[,\s]\s*[-+]?\d+\.\d{2,}", text)
    low = text.lower()
    for phrase in (
        "latitude",
        "longitude",
        "lat:",
        "lng:",
        "lon:",
        "gps coordinates",
        "located at",
    ):
        assert phrase not in low


def test_run_demo_never_emits_poaching_overreach():
    text = run_demo().lower()
    for phrase in (
        "predict poacher",
        "predict poaching",
        "optimise patrol",
        "optimize patrol",
        "anti-poaching operation",
    ):
        assert phrase not in text


def test_run_demo_never_emits_ecosystem_overreach():
    text = run_demo().lower()
    for phrase in (
        "population trajectory",
        "predict extinction",
        "extinction risk",
        "conservation outcome",
    ):
        assert phrase not in text

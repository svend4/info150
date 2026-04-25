"""Tests for AquacultureHealthEngine + synthetic pen + demo."""

from __future__ import annotations

import pytest

from triage4_fish.core.models import PenObservation
from triage4_fish.pen_health.monitoring_engine import (
    AquacultureHealthEngine,
)
from triage4_fish.pen_health.species_aquatic_bands import profile_for
from triage4_fish.sim.demo_runner import run_demo
from triage4_fish.sim.synthetic_pen import (
    demo_observations,
    generate_observation,
)


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


def test_profile_for_salmon():
    p = profile_for("salmon")
    assert p.species == "salmon"


def test_profile_for_tilapia_more_lenient():
    """Tilapia tolerates wider conditions — slightly looser
    thresholds than salmon."""
    salmon = profile_for("salmon")
    tilapia = profile_for("tilapia")
    assert tilapia.overall_urgent <= salmon.overall_urgent


def test_profile_for_unknown_raises():
    with pytest.raises(KeyError):
        profile_for("koi")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        AquacultureHealthEngine(weights={
            "gill_rate": 0, "school_cohesion": 0,
            "sea_lice": 0, "mortality_floor": 0,
            "water_chemistry": 0,
        })


def test_engine_empty_observation_neutral():
    obs = PenObservation(
        pen_id="P", species="salmon",
        location_handle="pen-A", window_duration_s=600.0,
    )
    report = AquacultureHealthEngine().review(obs)
    assert report.scores[0].overall == 1.0
    assert report.scores[0].welfare_level == "steady"


# ---------------------------------------------------------------------------
# Per-channel escalation
# ---------------------------------------------------------------------------


def test_engine_sea_lice_burden_escalates():
    obs = generate_observation(
        pen_id="P", sea_lice_burden=0.85, seed=1,
    )
    report = AquacultureHealthEngine().review(obs)
    lice_alerts = [a for a in report.alerts if a.kind == "sea_lice"]
    assert any(a.level == "urgent" for a in lice_alerts)


def test_engine_school_cohesion_lost_escalates():
    obs = generate_observation(
        pen_id="P", school_disruption=0.85, seed=2,
    )
    report = AquacultureHealthEngine().review(obs)
    school_alerts = [a for a in report.alerts if a.kind == "school_cohesion"]
    assert any(a.level == "urgent" for a in school_alerts)


def test_engine_water_chemistry_low_do_escalates():
    obs = generate_observation(
        pen_id="P", do_drop=0.85, seed=3,
    )
    report = AquacultureHealthEngine().review(obs)
    water_alerts = [a for a in report.alerts if a.kind == "water_chemistry"]
    assert any(a.level == "urgent" for a in water_alerts)


def test_engine_mortality_alone_escalates():
    """Mortality alone (no co-firing channel) emits a
    standalone candidate-mortality-cluster alert."""
    obs = generate_observation(
        pen_id="P", mortality_count=120, seed=4,
    )
    report = AquacultureHealthEngine().review(obs)
    mort_alerts = [a for a in report.alerts if a.kind == "mortality_floor"]
    assert any(a.level == "urgent" for a in mort_alerts)
    # Standalone mortality alert text is "candidate
    # mortality cluster" — surveillance-overreach-safe.
    text = mort_alerts[0].text.lower()
    assert "candidate mortality cluster" in text


# ---------------------------------------------------------------------------
# Cross-modal corroboration — the architectural feature
# ---------------------------------------------------------------------------


def test_engine_cross_modal_mortality_plus_water_chemistry():
    """When mortality AND water chemistry both fire urgent,
    the engine emits a SINGLE combined alert with the
    'candidate disease pattern (mortality cluster + water-
    chemistry stress)' framing."""
    obs = generate_observation(
        pen_id="P", mortality_count=120, do_drop=0.85, seed=5,
    )
    report = AquacultureHealthEngine().review(obs)
    mort_alerts = [a for a in report.alerts if a.kind == "mortality_floor"]
    water_alerts = [a for a in report.alerts if a.kind == "water_chemistry"]
    # Combined alert: ONE mortality_floor alert with the
    # corroborative wording, NO separate water_chemistry
    # alert (the water signal is folded into the combined
    # framing).
    assert len(mort_alerts) == 1
    assert mort_alerts[0].level == "urgent"
    text = mort_alerts[0].text.lower()
    assert "candidate disease pattern" in text
    assert "water-chemistry stress" in text
    # No separate water alert.
    assert water_alerts == []


def test_engine_cross_modal_mortality_plus_gill():
    obs = generate_observation(
        pen_id="P", mortality_count=120, gill_anomaly=0.95, seed=6,
    )
    report = AquacultureHealthEngine().review(obs)
    mort_alerts = [a for a in report.alerts if a.kind == "mortality_floor"]
    text = mort_alerts[0].text.lower()
    assert "gill-rate deviation" in text


# ---------------------------------------------------------------------------
# Multi-modal vision-confidence scaling
# ---------------------------------------------------------------------------


def test_engine_silt_storm_dampens_vision_channels():
    """Critical multi-modal property: under silt-storm
    conditions, the visible-light channels' weights are
    blended toward neutral. A pen with mild gill anomaly
    in clear water might escalate; the same anomaly in
    silt-storm should NOT escalate as readily."""
    obs_clear = generate_observation(
        pen_id="P", gill_anomaly=0.30,
        water_condition="clear", seed=7,
    )
    obs_silt = generate_observation(
        pen_id="P", gill_anomaly=0.30,
        water_condition="silt_storm", seed=7,
    )
    eng = AquacultureHealthEngine()
    silt_overall = eng.review(obs_silt).scores[0].overall
    clear_overall = eng.review(obs_clear).scores[0].overall
    # Silt-storm produces HIGHER overall (channels blend
    # toward neutral 1.0) — vision is less trustworthy.
    assert silt_overall >= clear_overall


def test_engine_calibration_alert_on_silt_storm():
    """When vision_confidence drops markedly AND no other
    alert fires, the engine surfaces a calibration alert
    so the farm manager knows the pass was less reliable."""
    obs = generate_observation(
        pen_id="P", water_condition="silt_storm", seed=8,
    )
    report = AquacultureHealthEngine().review(obs)
    calib_alerts = [a for a in report.alerts if a.kind == "calibration"]
    assert calib_alerts


# ---------------------------------------------------------------------------
# Determinism + invariants
# ---------------------------------------------------------------------------


def test_engine_is_deterministic():
    a = generate_observation(
        pen_id="det", mortality_count=50, do_drop=0.5, seed=11,
    )
    b = generate_observation(
        pen_id="det", mortality_count=50, do_drop=0.5, seed=11,
    )
    eng = AquacultureHealthEngine()
    ra = eng.review(a)
    rb = eng.review(b)
    assert ra.scores[0].overall == rb.scores[0].overall
    assert [al.text for al in ra.alerts] == [al.text for al in rb.alerts]


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        obs = generate_observation(
            pen_id=f"P{seed}",
            gill_anomaly=0.3, sea_lice_burden=0.3,
            do_drop=0.3, seed=seed,
        )
        report = AquacultureHealthEngine().review(obs)
        assert 0.0 <= report.scores[0].overall <= 1.0


# ---------------------------------------------------------------------------
# Synthetic pen + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(gill_anomaly=2.0)
    with pytest.raises(ValueError):
        generate_observation(school_disruption=-0.1)
    with pytest.raises(ValueError):
        generate_observation(sea_lice_burden=2.0)
    with pytest.raises(ValueError):
        generate_observation(mortality_count=-1)
    with pytest.raises(ValueError):
        generate_observation(do_drop=2.0)
    with pytest.raises(ValueError):
        generate_observation(window_duration_s=-5)


def test_demo_observations_length():
    assert len(demo_observations()) == 5


def test_demo_observations_deterministic():
    a = demo_observations()
    b = demo_observations()
    for oa, ob in zip(a, b):
        assert [s.rate_bpm for s in oa.gill_rate_samples] == \
               [s.rate_bpm for s in ob.gill_rate_samples]


def test_run_demo_covers_every_welfare_level():
    text = run_demo()
    for level in ("steady", "watch", "urgent"):
        assert level in text


# ---------------------------------------------------------------------------
# Property tests on demo output
# ---------------------------------------------------------------------------


def test_run_demo_uses_candidate_disease_pattern_framing():
    """When the demo's cross-modal pattern fires, the alert
    text uses the surveillance-overreach-safe 'candidate
    disease pattern' wording."""
    text = run_demo()
    assert "candidate disease pattern" in text


def test_run_demo_never_recommends_dosing():
    """Property test: the demo NEVER emits any antibiotic-
    dosing-overreach phrase even though one demo session
    triggers a disease-pattern alert."""
    text = run_demo().lower()
    for phrase in (
        "administer antibiotic",
        "administer antimicrobial",
        "dose with",
        "dosing recommendation",
        "prescribe antimicrobial",
        "prescribe antibiotic",
        "treatment regimen",
        "course of treatment",
        "withdrawal period",
        "oxytetracycline",
        "florfenicol",
        "emamectin",
        "azamethiphos",
        "medicated feed",
    ):
        assert phrase not in text


def test_run_demo_never_emits_outbreak_overreach():
    text = run_demo().lower()
    for phrase in (
        "outbreak detected",
        "outbreak confirmed",
        "epidemic",
        "pandemic",
        "disease confirmed",
        "isa confirmed",
        "isav confirmed",
        "pd confirmed",
        "ipn confirmed",
        "sav confirmed",
    ):
        assert phrase not in text


def test_run_demo_never_emits_reassurance():
    text = run_demo().lower()
    for phrase in (
        "pen is healthy",
        "no outbreak",
        "stock is safe",
        "stocks are safe",
        "clean bill of health",
        "all pens safe",
        "disease-free",
    ):
        assert phrase not in text


def test_run_demo_never_emits_decimal_coords():
    import re
    text = run_demo()
    assert not re.search(
        r"[-+]?\d+\.\d{2,}\s*[,\s]\s*[-+]?\d+\.\d{2,}", text,
    )


def test_run_demo_uses_vet_review_recommended_framing():
    """Every urgent alert in the demo routes the decision
    to a vet — 'consult vet' / 'vet review recommended'
    framing rather than dosing recommendation."""
    text = run_demo().lower()
    assert "vet review recommended" in text

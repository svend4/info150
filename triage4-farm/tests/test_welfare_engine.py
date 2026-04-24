"""Tests for WelfareCheckEngine + synthetic herd."""

from __future__ import annotations

import pytest

from triage4_farm.core.models import (
    AnimalObservation,
    JointPoseSample,
)
from triage4_farm.sim.demo_runner import run_demo
from triage4_farm.sim.synthetic_herd import demo_herd, generate_observation
from triage4_farm.welfare_check.species_profiles import (
    SpeciesProfile,
    profile_for,
)
from triage4_farm.welfare_check.welfare_engine import WelfareCheckEngine


# ---------------------------------------------------------------------------
# profile_for
# ---------------------------------------------------------------------------


def test_profile_for_cow():
    p = profile_for("dairy_cow")
    assert isinstance(p, SpeciesProfile)
    assert p.lameness_pairs != ()


def test_profile_for_chicken_has_empty_pair_list():
    p = profile_for("chicken")
    assert p.lameness_pairs == ()


def test_profile_for_unknown_raises():
    with pytest.raises(KeyError):
        profile_for("alpaca")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# generate_observation + demo_herd
# ---------------------------------------------------------------------------


def test_generate_observation_is_deterministic():
    a = generate_observation("A1", "dairy_cow", seed=0)
    b = generate_observation("A1", "dairy_cow", seed=0)
    assert len(a.pose_frames) == len(b.pose_frames)
    assert a.pose_frames[0][0].y == b.pose_frames[0][0].y


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation("A1", "dairy_cow", duration_s=-1)
    with pytest.raises(ValueError):
        generate_observation("A1", "dairy_cow", lameness_severity=2.0)
    with pytest.raises(ValueError):
        generate_observation("A1", "dairy_cow", respiratory_elevation=2.0)
    with pytest.raises(ValueError):
        generate_observation("A1", "dairy_cow", n_frames=2)


def test_demo_herd_size():
    herd = demo_herd(n_animals=5, n_lame=2)
    assert len(herd) == 5
    assert all(o.species == "dairy_cow" for o in herd)


def test_demo_herd_rejects_too_many_lame():
    with pytest.raises(ValueError):
        demo_herd(n_animals=3, n_lame=4)


# ---------------------------------------------------------------------------
# WelfareCheckEngine
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        WelfareCheckEngine(weights={"gait": 0, "respiratory": 0, "thermal": 0})


def test_engine_handles_empty_observations():
    report = WelfareCheckEngine().review(farm_id="F1", observations=[])
    assert report.scores == []
    assert len(report.alerts) == 1
    assert report.alerts[0].kind == "behaviour"


def test_engine_healthy_herd_has_no_alerts():
    herd = demo_herd(n_animals=4, n_lame=0)
    report = WelfareCheckEngine().review(farm_id="F1", observations=herd)
    assert report.alerts_at_flag("urgent") == []
    assert report.alerts_at_flag("concern") == []
    assert all(s.flag == "well" for s in report.scores)


def test_engine_lame_animals_surface_alerts():
    herd = demo_herd(n_animals=6, n_lame=2)
    report = WelfareCheckEngine().review(farm_id="F1", observations=herd)
    assert len(report.alerts_at_flag("concern")) >= 2
    lameness_alerts = [a for a in report.alerts if a.kind == "lameness"]
    assert len(lameness_alerts) >= 1


def test_engine_severe_lameness_triggers_urgent_alert():
    """Hand-crafted observation with every bilateral pair offset
    forces the urgent lameness threshold. Kept as a unit test
    rather than a demo_herd call because demo_herd tunes severity
    to the concern band."""
    frames: list[list[JointPoseSample]] = []
    for _ in range(8):
        frames.append([
            JointPoseSample(joint="wither",    x=0.30, y=0.30),
            JointPoseSample(joint="rump",      x=0.70, y=0.30),
            JointPoseSample(joint="hock_l",    x=0.68, y=0.50),
            JointPoseSample(joint="hock_r",    x=0.72, y=0.75),
            JointPoseSample(joint="fetlock_l", x=0.68, y=0.60),
            JointPoseSample(joint="fetlock_r", x=0.72, y=0.85),
            JointPoseSample(joint="hoof_l",    x=0.68, y=0.70),
            JointPoseSample(joint="hoof_r",    x=0.72, y=0.95),
        ])
    obs = AnimalObservation(
        animal_id="BAD1",
        species="dairy_cow",
        pose_frames=frames,
        duration_s=2.5,
    )
    report = WelfareCheckEngine().review(farm_id="F1", observations=[obs])
    urgent = report.alerts_at_flag("urgent")
    assert any(a.kind == "lameness" for a in urgent), (
        f"expected urgent lameness alert, got "
        f"gait={report.scores[0].gait:.2f}"
    )


def test_engine_overall_in_unit_interval():
    herd = demo_herd(n_animals=4, n_lame=1)
    report = WelfareCheckEngine().review(farm_id="F1", observations=herd)
    assert 0.0 <= report.herd_overall <= 1.0
    for s in report.scores:
        assert 0.0 <= s.overall <= 1.0


def test_engine_scores_preserve_animal_order():
    herd = demo_herd(n_animals=5, n_lame=1)
    report = WelfareCheckEngine().review(farm_id="F1", observations=herd)
    expected_ids = [o.animal_id for o in herd]
    assert [s.animal_id for s in report.scores] == expected_ids


def test_engine_missing_channels_drop_out_of_weighted_mean():
    # A healthy animal with no IR + no respiratory sensor — the
    # overall should equal the gait score (only channel with a
    # signal) and the flag should be "well".
    frames = [
        [
            JointPoseSample(joint="wither", x=0.30, y=0.30),
            JointPoseSample(joint="rump",   x=0.70, y=0.30),
            JointPoseSample(joint="hock_l", x=0.68, y=0.70),
            JointPoseSample(joint="hock_r", x=0.72, y=0.70),
        ]
    ]
    obs = AnimalObservation(
        animal_id="A1",
        species="dairy_cow",
        pose_frames=frames,
        duration_s=2.0,
    )
    report = WelfareCheckEngine().review(farm_id="F1", observations=[obs])
    # Only gait contributed, gait was textbook → overall 1.0.
    assert report.scores[0].overall == 1.0
    assert report.scores[0].flag == "well"
    # No alerts surfaced — no sensor readings to complain about.
    assert report.alerts == []


def test_engine_is_deterministic():
    herd_a = demo_herd(n_animals=5, n_lame=2, seed=1)
    herd_b = demo_herd(n_animals=5, n_lame=2, seed=1)
    report_a = WelfareCheckEngine().review(farm_id="F1", observations=herd_a)
    report_b = WelfareCheckEngine().review(farm_id="F1", observations=herd_b)
    assert report_a.herd_overall == report_b.herd_overall
    assert [a.text for a in report_a.alerts] == [a.text for a in report_b.alerts]


def test_engine_as_text_mentions_farm_id():
    herd = demo_herd(n_animals=3, n_lame=0)
    report = WelfareCheckEngine().review(farm_id="my_farm", observations=herd)
    text = report.as_text()
    assert "my_farm" in text


def test_engine_chicken_uses_neutral_gait():
    # Chickens have no bilateral-pair set → gait channel falls
    # back to 1.0 regardless of pose frames. An anatomically
    # asymmetric bird should still not trigger a lameness alert,
    # because lameness in birds is scored differently upstream.
    frames = [
        [
            JointPoseSample(joint="keel", x=0.50, y=0.50),
            JointPoseSample(joint="shank_l", x=0.48, y=0.95),
            JointPoseSample(joint="shank_r", x=0.52, y=0.60),  # pronounced offset
        ]
    ]
    obs = AnimalObservation(
        animal_id="B1",
        species="chicken",
        pose_frames=frames,
        duration_s=1.5,
    )
    report = WelfareCheckEngine().review(farm_id="F1", observations=[obs])
    assert report.scores[0].gait == 1.0
    assert not any(a.kind == "lameness" for a in report.alerts)


# ---------------------------------------------------------------------------
# Demo runner — end-to-end smoke test.
# ---------------------------------------------------------------------------


def test_run_demo_produces_alerts():
    text = run_demo()
    assert "demo_farm" in text
    assert "CONCERN" in text

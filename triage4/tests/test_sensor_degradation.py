import pytest

from triage4.core.models import CasualtySignature
from triage4.sim import DegradationConfig, SensorDegradationSimulator


def _critical_sig() -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.1, 0.15, 0.2, 0.15],
        chest_motion_fd=0.2,
        perfusion_drop_score=0.8,
        bleeding_visual_score=0.9,
        thermal_asymmetry_score=0.6,
        posture_instability_score=0.5,
        visibility_score=1.0,
    )


def test_degradation_config_validation():
    with pytest.raises(ValueError):
        DegradationConfig(noise_sigma=1.5)
    with pytest.raises(ValueError):
        DegradationConfig(occlusion_prob=-0.1)
    with pytest.raises(ValueError):
        DegradationConfig(visibility_drop=2.0)


def test_noise_degrades_scores_deterministically():
    sim_a = SensorDegradationSimulator(
        DegradationConfig(noise_sigma=0.3), seed=42
    )
    sim_b = SensorDegradationSimulator(
        DegradationConfig(noise_sigma=0.3), seed=42
    )
    a = sim_a.apply(_critical_sig())
    b = sim_b.apply(_critical_sig())
    assert a.bleeding_visual_score == b.bleeding_visual_score
    assert a.perfusion_drop_score == b.perfusion_drop_score


def test_noise_stays_in_unit_interval():
    sim = SensorDegradationSimulator(DegradationConfig(noise_sigma=0.9), seed=1)
    out = sim.apply(_critical_sig())
    for score in (
        out.bleeding_visual_score,
        out.perfusion_drop_score,
        out.thermal_asymmetry_score,
        out.chest_motion_fd,
        out.posture_instability_score,
        out.visibility_score,
    ):
        assert 0.0 <= score <= 1.0


def test_visibility_drop_reduces_visibility():
    sim = SensorDegradationSimulator(
        DegradationConfig(visibility_drop=0.4), seed=0
    )
    out = sim.apply(_critical_sig())
    assert out.visibility_score <= 1.0 - 0.4 + 1e-9


def test_occlusion_zeroes_one_channel_on_hit():
    sim = SensorDegradationSimulator(
        DegradationConfig(occlusion_prob=1.0, noise_sigma=0.0), seed=3
    )
    out = sim.apply(_critical_sig())
    # One of the five scores must be zero (occluded).
    zero_channels = sum(
        1
        for v in (
            out.bleeding_visual_score,
            out.perfusion_drop_score,
            out.thermal_asymmetry_score,
            out.chest_motion_fd,
            out.posture_instability_score,
        )
        if v == 0.0
    )
    assert zero_channels >= 1


def test_drop_breathing_can_empty_curve():
    sim = SensorDegradationSimulator(
        DegradationConfig(drop_breathing_prob=1.0, noise_sigma=0.0), seed=0
    )
    out = sim.apply(_critical_sig())
    assert out.breathing_curve == []


def test_apply_many_returns_list():
    sim = SensorDegradationSimulator(DegradationConfig(noise_sigma=0.1), seed=0)
    outs = sim.apply_many([_critical_sig(), _critical_sig()])
    assert len(outs) == 2

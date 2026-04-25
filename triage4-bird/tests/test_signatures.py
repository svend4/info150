"""Tests for the five avian-monitoring signatures."""

from __future__ import annotations

from triage4_bird.core.models import (
    BodyThermalSample,
    CallSample,
    DeadBirdCandidate,
    WingbeatSample,
)
from triage4_bird.signatures.call_presence import (
    compute_call_presence_safety,
)
from triage4_bird.signatures.distress_rate import compute_distress_safety
from triage4_bird.signatures.febrile_thermal import (
    compute_febrile_thermal_safety,
)
from triage4_bird.signatures.mortality_cluster import (
    compute_mortality_cluster_safety,
)
from triage4_bird.signatures.wingbeat_vitals import compute_wingbeat_safety


# ---------------------------------------------------------------------------
# call_presence
# ---------------------------------------------------------------------------


def test_call_presence_no_expectation_returns_one():
    assert compute_call_presence_safety([], expected_species=()) == 1.0


def test_call_presence_all_expected_present():
    samples = [
        CallSample(t_s=0, species="robin", kind="song", confidence=0.8),
        CallSample(t_s=1, species="sparrow", kind="chip", confidence=0.7),
        CallSample(t_s=2, species="finch", kind="song", confidence=0.9),
    ]
    score = compute_call_presence_safety(
        samples, expected_species=("robin", "sparrow", "finch"),
    )
    assert score == 1.0


def test_call_presence_none_expected_present():
    samples = [
        CallSample(t_s=0, species="unknown", kind="song", confidence=0.8),
    ]
    score = compute_call_presence_safety(
        samples, expected_species=("robin", "sparrow", "finch"),
    )
    # Soft floor at 0.5.
    assert score == 0.5


def test_call_presence_partial_present():
    samples = [
        CallSample(t_s=0, species="robin", kind="song", confidence=0.8),
    ]
    score = compute_call_presence_safety(
        samples, expected_species=("robin", "sparrow", "finch"),
    )
    # 1/3 present → 0.5 + 0.5*0.333 ≈ 0.667.
    assert 0.6 < score < 0.7


def test_call_presence_low_confidence_doesnt_count():
    samples = [
        CallSample(t_s=0, species="robin", kind="song", confidence=0.2),
    ]
    score = compute_call_presence_safety(
        samples, expected_species=("robin",),
    )
    # Below confidence floor → no detection → 0.5 floor.
    assert score == 0.5


# ---------------------------------------------------------------------------
# distress_rate
# ---------------------------------------------------------------------------


def test_distress_empty_returns_one():
    assert compute_distress_safety([]) == 1.0


def test_distress_no_distress_calls_returns_one():
    samples = [
        CallSample(t_s=i, species="robin", kind="song", confidence=0.8)
        for i in range(5)
    ]
    assert compute_distress_safety(samples) == 1.0


def test_distress_all_distress_returns_zero():
    samples = [
        CallSample(t_s=i, species="robin", kind="distress", confidence=0.8)
        for i in range(5)
    ]
    assert compute_distress_safety(samples) == 0.0


def test_distress_partial_returns_partial():
    samples = [
        CallSample(t_s=i, species="robin", kind="song", confidence=0.8)
        for i in range(8)
    ]
    samples.extend([
        CallSample(t_s=8 + i, species="robin", kind="distress", confidence=0.8)
        for i in range(2)
    ])
    # 20 % distress → 1 - 0.20/0.30 = 0.333.
    score = compute_distress_safety(samples)
    assert 0.2 < score < 0.5


def test_distress_low_confidence_filtered():
    samples = [
        CallSample(t_s=i, species="robin", kind="distress", confidence=0.2)
        for i in range(5)
    ]
    # All below confidence floor → empty after filter → 1.0.
    assert compute_distress_safety(samples) == 1.0


# ---------------------------------------------------------------------------
# wingbeat_vitals
# ---------------------------------------------------------------------------


def test_wingbeat_empty_returns_one():
    assert compute_wingbeat_safety([]) == 1.0


def test_wingbeat_unreliable_only_returns_one():
    samples = [
        WingbeatSample(t_s=i, frequency_hz=30.0, reliable=False)
        for i in range(5)
    ]
    assert compute_wingbeat_safety(samples) == 1.0


def test_wingbeat_in_band_returns_one():
    samples = [
        WingbeatSample(t_s=i, frequency_hz=8.0, reliable=True)
        for i in range(5)
    ]
    assert compute_wingbeat_safety(samples) == 1.0


def test_wingbeat_above_cap_returns_zero():
    samples = [
        WingbeatSample(t_s=i, frequency_hz=30.0, reliable=True)
        for i in range(5)
    ]
    assert compute_wingbeat_safety(samples) == 0.0


def test_wingbeat_partial_above_band():
    samples = [
        WingbeatSample(t_s=i, frequency_hz=18.0, reliable=True)
        for i in range(5)
    ]
    score = compute_wingbeat_safety(samples)
    # 18 in (12, 25) → linear decay.
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# febrile_thermal
# ---------------------------------------------------------------------------


def test_thermal_empty_returns_one():
    assert compute_febrile_thermal_safety([]) == 1.0


def test_thermal_no_elevation_returns_one():
    samples = [BodyThermalSample(t_s=i, elevation=0.0) for i in range(5)]
    assert compute_febrile_thermal_safety(samples) == 1.0


def test_thermal_full_elevation_returns_zero():
    samples = [BodyThermalSample(t_s=i, elevation=1.0) for i in range(5)]
    assert compute_febrile_thermal_safety(samples) == 0.0


def test_thermal_partial_elevation():
    samples = [BodyThermalSample(t_s=i, elevation=0.5) for i in range(5)]
    score = compute_febrile_thermal_safety(samples)
    assert score == 0.5


# ---------------------------------------------------------------------------
# mortality_cluster
# ---------------------------------------------------------------------------


def test_mortality_empty_returns_one():
    assert compute_mortality_cluster_safety([]) == 1.0


def test_mortality_low_confidence_filtered():
    candidates = [
        DeadBirdCandidate(t_s=i, confidence=0.3) for i in range(10)
    ]
    # All below confidence floor → safety stays at 1.0.
    assert compute_mortality_cluster_safety(candidates) == 1.0


def test_mortality_high_count_returns_zero():
    candidates = [
        DeadBirdCandidate(t_s=i, confidence=0.9) for i in range(8)
    ]
    # weighted_count = 7.2 > 5.0 high cap → safety 0.
    assert compute_mortality_cluster_safety(candidates) == 0.0


def test_mortality_partial_count():
    candidates = [
        DeadBirdCandidate(t_s=i, confidence=0.7) for i in range(3)
    ]
    score = compute_mortality_cluster_safety(candidates)
    # weighted_count = 2.1 → safety 1 - 2.1/5.0 = 0.58.
    assert 0.4 < score < 0.7

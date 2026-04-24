"""Tests for fall / activity / mobility signatures."""

from __future__ import annotations

from triage4_home.core.models import (
    ActivitySample,
    ImpactSample,
    RoomTransition,
)
from triage4_home.signatures.activity_pattern import (
    ActivityFractions,
    compute_activity_alignment,
    compute_fractions,
)
from triage4_home.signatures.fall_signature import (
    classify_impact,
    compute_fall_risk,
)
from triage4_home.signatures.mobility_pace import (
    compute_mobility_trend,
    compute_transition_paces,
)


# ---------------------------------------------------------------------------
# fall_signature
# ---------------------------------------------------------------------------


def test_classify_impact_below_threshold_none():
    s = ImpactSample(t_s=1.0, magnitude_g=1.2, stillness_after_s=0.0)
    assert classify_impact(s, impact_threshold_g=2.0,
                           stillness_threshold_s=8.0) == "none"


def test_classify_impact_high_short_stillness_borderline():
    s = ImpactSample(t_s=1.0, magnitude_g=3.0, stillness_after_s=2.0)
    assert classify_impact(s, impact_threshold_g=2.0,
                           stillness_threshold_s=8.0) == "borderline"


def test_classify_impact_full_candidate():
    s = ImpactSample(t_s=1.0, magnitude_g=3.0, stillness_after_s=12.0)
    assert classify_impact(s, impact_threshold_g=2.0,
                           stillness_threshold_s=8.0) == "candidate"


def test_fall_risk_empty_returns_zero():
    score, band = compute_fall_risk([])
    assert score == 0.0
    assert band == "none"


def test_fall_risk_single_candidate_returns_one():
    samples = [ImpactSample(t_s=1, magnitude_g=3.0, stillness_after_s=12.0)]
    score, band = compute_fall_risk(samples)
    assert score == 1.0
    assert band == "candidate"


def test_fall_risk_borderline_partial_score():
    samples = [ImpactSample(t_s=1, magnitude_g=3.0, stillness_after_s=4.0)]
    score, band = compute_fall_risk(samples)
    assert 0.0 < score < 1.0
    assert band == "borderline"


def test_fall_risk_worst_band_dominates():
    # Mix of below-threshold, borderline, and candidate.
    samples = [
        ImpactSample(t_s=1, magnitude_g=1.2, stillness_after_s=0.0),
        ImpactSample(t_s=2, magnitude_g=3.0, stillness_after_s=4.0),
        ImpactSample(t_s=3, magnitude_g=3.0, stillness_after_s=15.0),
    ]
    score, band = compute_fall_risk(samples)
    assert score == 1.0
    assert band == "candidate"


# ---------------------------------------------------------------------------
# activity_pattern
# ---------------------------------------------------------------------------


def test_compute_fractions_empty_returns_zero():
    f = compute_fractions([])
    assert f == ActivityFractions(resting=0.0, light=0.0, moderate=0.0)


def test_compute_fractions_fifty_fifty():
    samples = [
        ActivitySample(t_s=0, intensity="resting"),
        ActivitySample(t_s=1, intensity="moderate"),
    ]
    f = compute_fractions(samples)
    assert f.resting == 0.5
    assert f.moderate == 0.5


def test_fractions_coverage_excludes_unknown():
    samples = [
        ActivitySample(t_s=0, intensity="resting"),
        ActivitySample(t_s=1, intensity="unknown"),
    ]
    f = compute_fractions(samples)
    assert f.coverage == 0.5


def test_activity_alignment_matches_baseline():
    baseline = ActivityFractions(resting=0.35, light=0.45, moderate=0.20)
    # Construct a sample set matching baseline exactly.
    samples: list[ActivitySample] = []
    # 7 resting + 9 light + 4 moderate = 20 total (matches)
    for i in range(7):
        samples.append(ActivitySample(t_s=i, intensity="resting"))
    for i in range(9):
        samples.append(ActivitySample(t_s=7 + i, intensity="light"))
    for i in range(4):
        samples.append(ActivitySample(t_s=16 + i, intensity="moderate"))
    alignment = compute_activity_alignment(samples, baseline)
    assert alignment == 1.0


def test_activity_alignment_diverges_from_baseline():
    baseline = ActivityFractions(resting=0.35, light=0.45, moderate=0.20)
    # All resting — maximal deviation from the baseline.
    samples = [ActivitySample(t_s=i, intensity="resting") for i in range(10)]
    alignment = compute_activity_alignment(samples, baseline)
    assert 0.0 <= alignment < 0.5


def test_activity_alignment_without_baseline_is_neutral():
    samples = [ActivitySample(t_s=i, intensity="light") for i in range(10)]
    assert compute_activity_alignment(samples, None) == 1.0


def test_activity_alignment_low_coverage_caps_score():
    baseline = ActivityFractions(resting=0.35, light=0.45, moderate=0.20)
    # 90 % unknown, 10 % moderate — low coverage.
    samples = [ActivitySample(t_s=i, intensity="unknown") for i in range(9)]
    samples.append(ActivitySample(t_s=9, intensity="moderate"))
    alignment = compute_activity_alignment(samples, baseline)
    # Low coverage: score should not go low — at worst a
    # neutral 0.5. The signature deliberately refuses to
    # punish the resident for sparse sensor data.
    assert alignment >= 0.5


# ---------------------------------------------------------------------------
# mobility_pace
# ---------------------------------------------------------------------------


def test_paces_empty_returns_empty():
    assert compute_transition_paces([]) == []


def test_paces_uses_transition_duration():
    # 4 m in 4 s → 1.0 m/s.
    t = RoomTransition(
        t_s=10.0, from_room="kitchen", to_room="living",
        distance_m=4.0, duration_s=4.0,
    )
    paces = compute_transition_paces([t])
    assert paces == [1.0]


def test_paces_filters_nonsense_values():
    # 4 m in 0.5 s = 8 m/s — way above the max-sane cap.
    t_fast = RoomTransition(
        t_s=10.0, from_room="kitchen", to_room="living",
        distance_m=4.0, duration_s=0.5,
    )
    # 4 m in 300 s = 0.013 m/s — below the min-sane floor.
    t_slow = RoomTransition(
        t_s=20.0, from_room="living", to_room="kitchen",
        distance_m=4.0, duration_s=300.0,
    )
    paces = compute_transition_paces([t_fast, t_slow])
    assert paces == []


def test_mobility_trend_no_data_neutral():
    median, score = compute_mobility_trend([])
    assert median == 0.0
    assert score == 0.5


def test_mobility_trend_at_or_above_baseline_is_one():
    transitions = [
        RoomTransition(t_s=i * 10, from_room="kitchen", to_room="living",
                       distance_m=4.0, duration_s=4.0)
        for i in range(5)
    ]
    # Median 1.0 m/s vs baseline 0.9 → score 1.0.
    median, score = compute_mobility_trend(transitions, baseline_median_mps=0.9)
    assert median == 1.0
    assert score == 1.0


def test_mobility_trend_well_below_baseline_is_zero():
    # 4 m in 8 s = 0.5 m/s. Baseline 1.0. Decline threshold
    # 0.15 → floor = 0.85 m/s → 0.5 < 0.85 → score 0.0.
    transitions = [
        RoomTransition(t_s=i * 10, from_room="kitchen", to_room="living",
                       distance_m=4.0, duration_s=8.0)
        for i in range(5)
    ]
    median, score = compute_mobility_trend(transitions, baseline_median_mps=1.0)
    assert median == 0.5
    assert score == 0.0


def test_mobility_trend_partial_decline():
    # 4 m in 4.5 s = 0.889 m/s. Baseline 1.0 → floor 0.85.
    # Just above the floor.
    transitions = [
        RoomTransition(t_s=i * 10, from_room="kitchen", to_room="living",
                       distance_m=4.0, duration_s=4.5)
        for i in range(5)
    ]
    median, score = compute_mobility_trend(transitions, baseline_median_mps=1.0)
    assert 0.0 < score < 1.0

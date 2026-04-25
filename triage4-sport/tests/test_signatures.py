"""Tests for the four sport-performance signatures."""

from __future__ import annotations

from triage4_sport.core.models import (
    MovementSample,
    RecoveryHRSample,
    WorkloadSample,
)
from triage4_sport.signatures.baseline_deviation import (
    compute_baseline_deviation_safety,
)
from triage4_sport.signatures.form_asymmetry import (
    compute_form_asymmetry_safety,
)
from triage4_sport.signatures.recovery_hr import compute_recovery_hr_safety
from triage4_sport.signatures.workload_load import compute_workload_safety


# ---------------------------------------------------------------------------
# form_asymmetry
# ---------------------------------------------------------------------------


def test_form_empty_returns_one():
    assert compute_form_asymmetry_safety([]) == 1.0


def test_form_at_baseline_is_one():
    samples = [
        MovementSample(t_s=i, kind="kick", form_asymmetry=0.15, range_of_motion=0.85)
        for i in range(5)
    ]
    assert compute_form_asymmetry_safety(samples, typical_baseline=0.15) == 1.0


def test_form_below_baseline_is_one():
    samples = [
        MovementSample(t_s=i, kind="kick", form_asymmetry=0.10, range_of_motion=0.85)
        for i in range(5)
    ]
    assert compute_form_asymmetry_safety(samples, typical_baseline=0.20) == 1.0


def test_form_above_baseline_drops():
    samples = [
        MovementSample(t_s=i, kind="kick", form_asymmetry=0.40, range_of_motion=0.7)
        for i in range(5)
    ]
    score = compute_form_asymmetry_safety(samples, typical_baseline=0.15)
    # Deviation 0.25 in (0, 0.30) → partial-band score.
    assert 0.0 < score < 0.5


def test_form_far_above_baseline_returns_zero():
    samples = [
        MovementSample(t_s=i, kind="kick", form_asymmetry=0.55, range_of_motion=0.5)
        for i in range(5)
    ]
    assert compute_form_asymmetry_safety(
        samples, typical_baseline=0.10,
    ) == 0.0


def test_form_no_baseline_uses_absolute_threshold():
    samples = [
        MovementSample(t_s=i, kind="kick", form_asymmetry=0.15, range_of_motion=0.85)
        for i in range(5)
    ]
    # No baseline → absolute heuristic; 0.15 is below 0.20 → 1.0.
    assert compute_form_asymmetry_safety(samples) == 1.0


# ---------------------------------------------------------------------------
# workload_load
# ---------------------------------------------------------------------------


def test_workload_empty_returns_one():
    assert compute_workload_safety([]) == 1.0


def test_workload_low_session_returns_one():
    samples = [
        WorkloadSample(
            t_s=3600, distance_m=4000, high_speed_runs=20,
            accelerations=40, decelerations=40,
        ),
    ]
    score = compute_workload_safety(samples, typical_baseline=0.50)
    assert score == 1.0


def test_workload_acute_spike_returns_zero():
    samples = [
        WorkloadSample(
            t_s=3600, distance_m=14000, high_speed_runs=200,
            accelerations=200, decelerations=200,
        ),
    ]
    score = compute_workload_safety(samples, typical_baseline=0.50)
    assert score == 0.0


def test_workload_partial_spike():
    samples = [
        WorkloadSample(
            t_s=3600, distance_m=9000, high_speed_runs=85,
            accelerations=120, decelerations=120,
        ),
    ]
    score = compute_workload_safety(samples, typical_baseline=0.50)
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# recovery_hr
# ---------------------------------------------------------------------------


def test_recovery_empty_returns_one():
    assert compute_recovery_hr_safety([]) == 1.0


def test_recovery_good_drop_is_one():
    samples = [
        RecoveryHRSample(t_s=i, peak_hr_bpm=170, recovery_drop_bpm=35)
        for i in range(3)
    ]
    assert compute_recovery_hr_safety(samples) == 1.0


def test_recovery_poor_drop_is_zero():
    samples = [
        RecoveryHRSample(t_s=i, peak_hr_bpm=170, recovery_drop_bpm=8)
        for i in range(3)
    ]
    assert compute_recovery_hr_safety(samples) == 0.0


def test_recovery_partial():
    samples = [
        RecoveryHRSample(t_s=i, peak_hr_bpm=170, recovery_drop_bpm=20)
        for i in range(3)
    ]
    score = compute_recovery_hr_safety(samples)
    assert 0.0 < score < 1.0


def test_recovery_baseline_degradation_compounds():
    samples = [
        RecoveryHRSample(t_s=i, peak_hr_bpm=170, recovery_drop_bpm=18)
        for i in range(3)
    ]
    no_baseline = compute_recovery_hr_safety(samples)
    with_baseline = compute_recovery_hr_safety(
        samples, typical_baseline_bpm=35.0,
    )
    # Baseline degradation pushes safety lower than absolute
    # alone.
    assert with_baseline <= no_baseline


# ---------------------------------------------------------------------------
# baseline_deviation
# ---------------------------------------------------------------------------


def test_baseline_deviation_all_high_returns_one():
    assert compute_baseline_deviation_safety(1.0, 1.0, 1.0) == 1.0


def test_baseline_deviation_all_zero_returns_zero():
    assert compute_baseline_deviation_safety(0.0, 0.0, 0.0) == 0.0


def test_baseline_deviation_single_low_softer():
    """Single channel low → geometric mean is high — multi-
    channel deviation compounds, single channel doesn't."""
    score = compute_baseline_deviation_safety(0.2, 1.0, 1.0)
    # 0.2^(1/3) ≈ 0.585.
    assert 0.5 < score < 0.7


def test_baseline_deviation_multi_channel_compounds():
    score_single = compute_baseline_deviation_safety(0.4, 1.0, 1.0)
    score_multi = compute_baseline_deviation_safety(0.4, 0.4, 0.4)
    assert score_multi < score_single

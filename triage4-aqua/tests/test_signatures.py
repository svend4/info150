"""Tests for the four aquatic-safety signatures."""

from __future__ import annotations

from triage4_aqua.core.models import (
    SubmersionSample,
    SurfacePoseSample,
    SwimmerPresenceSample,
)
from triage4_aqua.signatures.absent_swimmer import (
    compute_absence_safety,
    longest_absence_s,
)
from triage4_aqua.signatures.idr_posture import compute_idr_safety
from triage4_aqua.signatures.submersion_duration import (
    compute_submersion_safety,
    longest_submersion_s,
)
from triage4_aqua.signatures.surface_distress import compute_distress_safety


# ---------------------------------------------------------------------------
# submersion_duration
# ---------------------------------------------------------------------------


def test_longest_submersion_empty_is_zero():
    assert longest_submersion_s([]) == 0.0


def test_longest_submersion_all_surface_is_zero():
    samples = [SubmersionSample(t_s=i, submerged=False) for i in range(10)]
    assert longest_submersion_s(samples) == 0.0


def test_longest_submersion_full_run_counts():
    samples = [SubmersionSample(t_s=i * 0.5, submerged=True) for i in range(10)]
    # 4.5 s from t=0 to t=4.5.
    assert longest_submersion_s(samples) == 4.5


def test_longest_submersion_interrupted_runs():
    samples = [
        SubmersionSample(t_s=0.0, submerged=True),
        SubmersionSample(t_s=5.0, submerged=True),
        SubmersionSample(t_s=10.0, submerged=False),
        SubmersionSample(t_s=12.0, submerged=True),
        SubmersionSample(t_s=14.0, submerged=True),
        SubmersionSample(t_s=16.0, submerged=False),
    ]
    # Longest run: 10 s (t=0 → t=10, the boundary sample
    # stops the run so measured length is 10 - 0 = 10).
    assert longest_submersion_s(samples) == 10.0


def test_submersion_safety_short_run_is_one():
    # 5 s submersion — well below 15 s watch threshold.
    samples = [
        SubmersionSample(t_s=i * 0.5, submerged=True) for i in range(11)
    ]
    # samples t=0..5.0
    assert compute_submersion_safety(samples) == 1.0


def test_submersion_safety_urgent_run_is_zero():
    # 35 s submersion — above 30 s urgent threshold.
    samples = [
        SubmersionSample(t_s=i * 0.5, submerged=True) for i in range(71)
    ]
    assert compute_submersion_safety(samples) == 0.0


def test_submersion_safety_partial_band():
    # 22 s — inside watch-urgent band.
    samples = [
        SubmersionSample(t_s=i * 0.5, submerged=True) for i in range(45)
    ]
    # Longest run: 22 s.
    score = compute_submersion_safety(samples)
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# idr_posture
# ---------------------------------------------------------------------------


def test_idr_empty_returns_one():
    assert compute_idr_safety([]) == 1.0


def test_idr_all_normal_is_one():
    samples = [
        SurfacePoseSample(
            t_s=i, head_height_rel=0.8,
            body_vertical=0.2, motion_rhythm=0.9,
        )
        for i in range(10)
    ]
    assert compute_idr_safety(samples) == 1.0


def test_idr_all_idr_samples_is_zero():
    samples = [
        SurfacePoseSample(
            t_s=i, head_height_rel=0.15,
            body_vertical=0.9, motion_rhythm=0.1,
        )
        for i in range(10)
    ]
    assert compute_idr_safety(samples) == 0.0


def test_idr_partial_fraction_gives_partial_score():
    # 2 IDR + 8 normal = 0.2 IDR fraction → score = 1.0 - 0.4 = 0.6.
    samples = [
        SurfacePoseSample(
            t_s=i, head_height_rel=0.15,
            body_vertical=0.9, motion_rhythm=0.1,
        )
        for i in range(2)
    ]
    samples.extend([
        SurfacePoseSample(
            t_s=2 + i, head_height_rel=0.8,
            body_vertical=0.2, motion_rhythm=0.9,
        )
        for i in range(8)
    ])
    score = compute_idr_safety(samples)
    assert 0.5 < score < 0.7


def test_idr_partial_sample_doesnt_fire():
    # Low head but NOT vertical + rhythm — not IDR.
    samples = [
        SurfacePoseSample(
            t_s=i, head_height_rel=0.15,
            body_vertical=0.2, motion_rhythm=0.9,
        )
        for i in range(10)
    ]
    assert compute_idr_safety(samples) == 1.0


# ---------------------------------------------------------------------------
# absent_swimmer
# ---------------------------------------------------------------------------


def test_longest_absence_empty_is_zero():
    assert longest_absence_s([]) == 0.0


def test_longest_absence_all_active_is_zero_or_small():
    samples = [
        SwimmerPresenceSample(t_s=i, active=True) for i in range(10)
    ]
    # Max gap is 1 s between consecutive actives.
    assert longest_absence_s(samples) <= 1.0


def test_longest_absence_long_gap_detected():
    samples = [
        SwimmerPresenceSample(t_s=0, active=True),
        SwimmerPresenceSample(t_s=30, active=True),
    ]
    assert longest_absence_s(samples) == 30.0


def test_absence_safety_short_gap_is_one():
    samples = [
        SwimmerPresenceSample(t_s=i, active=True) for i in range(10)
    ]
    assert compute_absence_safety(samples) == 1.0


def test_absence_safety_long_gap_is_zero():
    samples = [
        SwimmerPresenceSample(t_s=0, active=True),
        SwimmerPresenceSample(t_s=60, active=True),
    ]
    assert compute_absence_safety(samples) == 0.0


def test_absence_safety_partial_band():
    samples = [
        SwimmerPresenceSample(t_s=0, active=True),
        SwimmerPresenceSample(t_s=30, active=True),
    ]
    score = compute_absence_safety(samples)
    # Gap = 30 s — inside 20-45 s band.
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# surface_distress
# ---------------------------------------------------------------------------


def test_distress_empty_returns_one():
    assert compute_distress_safety([]) == 1.0


def test_distress_all_normal_is_one():
    samples = [
        SurfacePoseSample(
            t_s=i, head_height_rel=0.8,
            body_vertical=0.2, motion_rhythm=0.9,
        )
        for i in range(10)
    ]
    assert compute_distress_safety(samples) == 1.0


def test_distress_majority_low_head_is_zero():
    samples = [
        SurfacePoseSample(
            t_s=i, head_height_rel=0.10,
            body_vertical=0.3, motion_rhythm=0.8,
        )
        for i in range(10)
    ]
    assert compute_distress_safety(samples) == 0.0


def test_distress_partial_low_head_partial_score():
    # 3 low-head + 7 normal = 0.3 fraction → 1 - 0.3/0.6 = 0.5.
    samples = [
        SurfacePoseSample(
            t_s=i, head_height_rel=0.10,
            body_vertical=0.3, motion_rhythm=0.8,
        )
        for i in range(3)
    ]
    samples.extend([
        SurfacePoseSample(
            t_s=3 + i, head_height_rel=0.8,
            body_vertical=0.2, motion_rhythm=0.9,
        )
        for i in range(7)
    ])
    score = compute_distress_safety(samples)
    assert 0.3 < score < 0.7

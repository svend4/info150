"""Tests for the K3-1.3 dynamic skeletal graph."""

from __future__ import annotations

import math

import pytest

from triage4.state_graph.skeletal_graph import (
    AsymmetryReport,
    JointObservation,
    JointTrend,
    SkeletalGraph,
    SkeletalSnapshot,
    UnknownJoint,
)


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------


def test_topology_lists_expected_joints():
    assert "head" in SkeletalGraph.JOINTS
    assert "pelvis" in SkeletalGraph.JOINTS
    assert len(SkeletalGraph.JOINTS) == 13


def test_mirror_pairs_are_left_right_only():
    for left, right in SkeletalGraph.MIRROR_PAIRS:
        assert left.endswith("_l")
        assert right.endswith("_r")
        assert left.removesuffix("_l") == right.removesuffix("_r")


def test_bones_reference_known_joints():
    known = set(SkeletalGraph.JOINTS)
    for a, b in SkeletalGraph.BONES:
        assert a in known
        assert b in known


# ---------------------------------------------------------------------------
# Recording + validation
# ---------------------------------------------------------------------------


def test_record_accepts_partial_joint_subset():
    g = SkeletalGraph()
    g.record(t=0.0, joints={"head": (1.0, 2.0)}, wounds={"head": 0.4})
    snap = g.latest()
    assert snap is not None
    assert "head" in snap.joints
    # pelvis / wrists etc. never observed — don't appear.
    assert "pelvis" not in snap.joints


def test_record_rejects_unknown_joint():
    g = SkeletalGraph()
    with pytest.raises(UnknownJoint):
        g.record(t=0.0, joints={"tail": (0.0, 0.0)})


def test_joint_observation_validates_wound_range():
    with pytest.raises(ValueError):
        JointObservation(t=0.0, x=0.0, y=0.0, wound_intensity=1.5)


def test_joint_observation_rejects_nonfinite():
    with pytest.raises(ValueError):
        JointObservation(t=float("inf"), x=0.0, y=0.0)


def test_max_history_bounds_memory():
    g = SkeletalGraph(max_history=5)
    for i in range(20):
        g.record(t=float(i), joints={"head": (float(i), 0.0)})
    assert g.joint_trend("head").n_observations == 5


def test_max_history_below_two_is_rejected():
    with pytest.raises(ValueError):
        SkeletalGraph(max_history=1)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_latest_returns_none_when_empty():
    assert SkeletalGraph().latest() is None


def test_latest_reports_most_recent_per_joint():
    g = SkeletalGraph()
    g.record(t=0.0, joints={"head": (0.0, 0.0)}, wounds={"head": 0.1})
    g.record(t=1.0, joints={"head": (5.0, 5.0)}, wounds={"head": 0.6})
    snap = g.latest()
    assert isinstance(snap, SkeletalSnapshot)
    assert snap.joints["head"] == (5.0, 5.0)
    assert snap.wounds["head"] == 0.6
    assert snap.t == 1.0


# ---------------------------------------------------------------------------
# Motion score
# ---------------------------------------------------------------------------


def test_motion_score_is_zero_for_stationary_joint():
    g = SkeletalGraph()
    for i in range(5):
        g.record(t=float(i), joints={"wrist_l": (2.0, 2.0)})
    assert g.joint_trend("wrist_l").motion_score == 0.0


def test_motion_score_rises_with_displacement():
    g = SkeletalGraph()
    for i in range(5):
        g.record(t=float(i), joints={"wrist_l": (float(i), 0.0)})
    trend = g.joint_trend("wrist_l")
    assert trend.motion_score > 0.0
    assert trend.motion_score <= 1.0


def test_motion_score_is_clipped_to_unit_interval():
    g = SkeletalGraph()
    # Huge displacement in 1s — the raw path length is enormous, but
    # the score must still be clipped to [0, 1].
    g.record(t=0.0, joints={"wrist_l": (0.0, 0.0)})
    g.record(t=1.0, joints={"wrist_l": (1_000.0, 0.0)})
    trend = g.joint_trend("wrist_l")
    assert 0.0 <= trend.motion_score <= 1.0


# ---------------------------------------------------------------------------
# Wound evolution
# ---------------------------------------------------------------------------


def test_wound_slope_positive_for_worsening_wound():
    g = SkeletalGraph()
    for i, w in enumerate([0.1, 0.3, 0.5, 0.7, 0.9]):
        g.record(t=float(i), joints={"torso_center": (0.0, 0.0)}
                 if "torso_center" in SkeletalGraph.JOINTS
                 else {"pelvis": (0.0, 0.0)},
                 wounds={"pelvis": w} if "torso_center" not in SkeletalGraph.JOINTS
                 else {"torso_center": w})
    trend = g.joint_trend("pelvis")
    assert trend.wound_slope > 0.1
    assert trend.wound_mean == pytest.approx(0.5, abs=1e-3)


def test_wound_slope_negative_for_healing_wound():
    g = SkeletalGraph()
    for i, w in enumerate([0.9, 0.7, 0.5, 0.3, 0.1]):
        g.record(t=float(i), joints={"head": (0.0, 0.0)}, wounds={"head": w})
    trend = g.joint_trend("head")
    assert trend.wound_slope < -0.1


def test_trend_on_joint_without_observations_is_zero():
    trend = SkeletalGraph().joint_trend("head")
    assert isinstance(trend, JointTrend)
    assert trend.n_observations == 0
    assert trend.motion_score == 0.0
    assert trend.wound_slope == 0.0


def test_joint_trend_rejects_unknown_joint():
    with pytest.raises(UnknownJoint):
        SkeletalGraph().joint_trend("tail")


# ---------------------------------------------------------------------------
# Asymmetry
# ---------------------------------------------------------------------------


def test_symmetric_motion_reports_near_zero_asymmetry():
    g = SkeletalGraph()
    for i in range(5):
        g.record(t=float(i),
                 joints={"wrist_l": (float(i), 0.0),
                         "wrist_r": (float(i), 0.0)})
    wrist_report = next(
        r for r in g.asymmetry()
        if r.pair == ("wrist_l", "wrist_r")
    )
    assert wrist_report.motion_asymmetry == 0.0


def test_asymmetric_motion_is_surfaced():
    """Left wrist moves, right wrist is still — high motion asymmetry."""
    g = SkeletalGraph()
    for i in range(5):
        g.record(
            t=float(i),
            joints={"wrist_l": (float(i), 0.0), "wrist_r": (0.0, 0.0)},
        )
    wrist_report = next(
        r for r in g.asymmetry() if r.pair == ("wrist_l", "wrist_r")
    )
    assert wrist_report.motion_asymmetry > 0.5


def test_asymmetric_wound_is_surfaced():
    g = SkeletalGraph()
    for i in range(5):
        g.record(
            t=float(i),
            joints={"hip_l": (0.0, 0.0), "hip_r": (0.0, 0.0)},
            wounds={"hip_l": 0.8, "hip_r": 0.05},
        )
    hip_report = next(
        r for r in g.asymmetry() if r.pair == ("hip_l", "hip_r")
    )
    assert hip_report.wound_asymmetry > 0.6


def test_asymmetry_skips_pairs_missing_observations():
    g = SkeletalGraph()
    for i in range(3):
        g.record(t=float(i), joints={"wrist_l": (float(i), 0.0)})
    # wrist_r never recorded → pair skipped, not present in report.
    reports = g.asymmetry()
    assert not any(r.pair == ("wrist_l", "wrist_r") for r in reports)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_as_json_round_trip_has_expected_keys():
    g = SkeletalGraph()
    g.record(t=0.0, joints={"head": (1.0, 2.0)}, wounds={"head": 0.3})
    out = g.as_json()
    assert "joints" in out
    assert "bones" in out
    assert "mirror_pairs" in out
    assert "latest" in out
    assert "n_observations" in out
    assert out["latest"]["t"] == 0.0


def test_as_json_latest_is_none_when_empty():
    assert SkeletalGraph().as_json()["latest"] is None


def test_dataclass_types_exported():
    assert AsymmetryReport and JointTrend and JointObservation and SkeletalSnapshot


def test_path_length_normalised_by_time_span():
    """Scaling time while scaling motion yields the same score."""
    g1 = SkeletalGraph()
    g2 = SkeletalGraph()
    for i in range(5):
        g1.record(t=float(i), joints={"wrist_l": (float(i), 0.0)})
        g2.record(t=float(i) * 2.0, joints={"wrist_l": (float(i) * 2.0, 0.0)})
    # Same shape in time/space → same normalised score.
    assert math.isclose(
        g1.joint_trend("wrist_l").motion_score,
        g2.joint_trend("wrist_l").motion_score,
        abs_tol=1e-6,
    )

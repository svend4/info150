"""Tests for RapidFormEngine + synthetic sim."""

from __future__ import annotations

import pytest

from triage4_fit.core.models import ExerciseSession, RepObservation
from triage4_fit.form_check.exercise_profiles import (
    ExerciseProfile,
    profile_for,
)
from triage4_fit.form_check.rapid_form_engine import RapidFormEngine
from triage4_fit.sim.synthetic_session import demo_session, generate_rep


# ---------------------------------------------------------------------------
# profile_for
# ---------------------------------------------------------------------------


def test_profile_for_squat_has_depth_joints():
    p = profile_for("squat")
    assert isinstance(p, ExerciseProfile)
    assert p.depth_joints != ()


def test_profile_for_unknown_raises():
    with pytest.raises(KeyError):
        profile_for("muscle-up")   # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# synthetic sim
# ---------------------------------------------------------------------------


def test_generate_rep_is_deterministic():
    a = generate_rep("squat", rep_index=0, seed=42)
    b = generate_rep("squat", rep_index=0, seed=42)
    assert len(a.samples) == len(b.samples)
    # Compare first-frame first-joint for byte-level repeatability.
    assert a.samples[0][0].x == b.samples[0][0].x
    assert a.samples[0][0].y == b.samples[0][0].y


def test_generate_rep_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_rep("squat", rep_index=0, duration_s=-1)
    with pytest.raises(ValueError):
        generate_rep("squat", rep_index=0, asymmetry_severity=2.0)
    with pytest.raises(ValueError):
        generate_rep("squat", rep_index=0, n_frames=2)


def test_demo_session_reps_count():
    sess = demo_session("squat", rep_count=4, asymmetry_severity=0.2)
    assert sess.rep_count == 4
    assert sess.exercise == "squat"


# ---------------------------------------------------------------------------
# RapidFormEngine
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        RapidFormEngine(weights={"symmetry": 0, "depth": 0, "tempo": 0})


def test_engine_handles_empty_session():
    sess = ExerciseSession(trainee_id="t1", exercise="squat")
    brief = RapidFormEngine().review(sess)
    assert brief.form_scores == []
    assert len(brief.cues) == 1
    assert brief.cues[0].kind == "tempo"


def test_engine_clean_session_has_no_severe_cues():
    # Symmetric, moderate asymmetry 0 — clean reps.
    sess = demo_session("squat", rep_count=3, asymmetry_severity=0.0)
    brief = RapidFormEngine().review(sess)
    severe = brief.cues_at_severity("severe")
    assert severe == []


def test_engine_high_asymmetry_triggers_severe_cue():
    """Hand-crafted rep with every bilateral pair offset forces the
    severe-symmetry threshold. Kept as a unit test rather than a
    demo_session call because the sim's asymmetry_severity bias
    only affects depth_joints (4 pairs out of 6) and averages out
    across the symmetry signature."""
    from triage4_fit.core.models import JointPoseSample

    frames: list[list[JointPoseSample]] = []
    for _ in range(8):
        frame = [
            JointPoseSample(joint="shoulder_l", x=0.45, y=0.30),
            JointPoseSample(joint="shoulder_r", x=0.55, y=0.38),
            JointPoseSample(joint="elbow_l",    x=0.40, y=0.45),
            JointPoseSample(joint="elbow_r",    x=0.60, y=0.55),
            JointPoseSample(joint="hip_l",      x=0.47, y=0.55),
            JointPoseSample(joint="hip_r",      x=0.53, y=0.70),
            JointPoseSample(joint="knee_l",     x=0.47, y=0.75),
            JointPoseSample(joint="knee_r",     x=0.53, y=0.90),
        ]
        frames.append(frame)

    bad_rep = RepObservation(rep_index=0, duration_s=2.5, samples=frames)
    sess = ExerciseSession(
        trainee_id="t1",
        exercise="squat",
        reps=[bad_rep],
    )
    brief = RapidFormEngine().review(sess)
    severe = brief.cues_at_severity("severe")
    assert len(severe) >= 1, (
        f"expected severe cue, got symmetry="
        f"{brief.form_scores[0].symmetry:.2f}"
    )
    assert any(c.kind == "asymmetry" for c in severe)


def test_engine_form_scores_sorted_by_rep_index():
    sess = demo_session("pushup", rep_count=5, asymmetry_severity=0.1)
    brief = RapidFormEngine().review(sess)
    indices = [s.rep_index for s in brief.form_scores]
    assert indices == sorted(indices)
    assert indices == [0, 1, 2, 3, 4]


def test_engine_overall_in_unit_interval():
    sess = demo_session("deadlift", rep_count=4, asymmetry_severity=0.4)
    brief = RapidFormEngine().review(sess)
    assert 0.0 <= brief.session_overall <= 1.0
    for s in brief.form_scores:
        assert 0.0 <= s.overall <= 1.0


def test_engine_slow_rep_triggers_severe_tempo_cue():
    # Build one rep taking 10 s — well past squat.tempo_high (6 s).
    slow_rep = generate_rep("squat", rep_index=0, duration_s=10.0)
    sess = ExerciseSession(
        trainee_id="t1",
        exercise="squat",
        reps=[slow_rep],
    )
    brief = RapidFormEngine().review(sess)
    tempo_cues = [c for c in brief.cues if c.kind == "tempo"]
    assert any(c.severity == "severe" for c in tempo_cues)


def test_engine_fast_rep_triggers_minor_tempo_cue():
    fast_rep = generate_rep("squat", rep_index=0, duration_s=0.4)
    sess = ExerciseSession(
        trainee_id="t1",
        exercise="squat",
        reps=[fast_rep],
    )
    brief = RapidFormEngine().review(sess)
    tempo_cues = [c for c in brief.cues if c.kind == "tempo"]
    assert any(c.severity == "minor" for c in tempo_cues)


def test_engine_recovery_cue_appears_when_vitals_elevated():
    # Custom last-rep with elevated HR (100 bpm, breathing 26).
    reps = [
        RepObservation(
            rep_index=i,
            duration_s=2.5,
            hr_bpm=100 + 2 * i,
            breathing_bpm=26 + i,
        )
        for i in range(3)
    ]
    sess = ExerciseSession(trainee_id="t1", exercise="squat", reps=reps)
    brief = RapidFormEngine().review(sess)
    breathing_cues = [c for c in brief.cues if c.kind == "breathing"]
    assert len(breathing_cues) == 1
    assert brief.recovery_quality is not None
    assert brief.recovery_quality < 0.5


def test_engine_no_recovery_cue_when_vitals_missing():
    reps = [RepObservation(rep_index=0, duration_s=2.5)]
    sess = ExerciseSession(trainee_id="t1", exercise="squat", reps=reps)
    brief = RapidFormEngine().review(sess)
    breathing_cues = [c for c in brief.cues if c.kind == "breathing"]
    assert breathing_cues == []
    assert brief.recovery_quality is None


def test_engine_as_text_mentions_session_overall():
    sess = demo_session("squat", rep_count=3)
    brief = RapidFormEngine().review(sess)
    text = brief.as_text()
    assert str(round(brief.session_overall, 2)) in text or "0." in text
    assert "squat" in text


def test_engine_is_deterministic():
    sess_a = demo_session("squat", rep_count=3, asymmetry_severity=0.3, seed=1)
    sess_b = demo_session("squat", rep_count=3, asymmetry_severity=0.3, seed=1)
    brief_a = RapidFormEngine().review(sess_a)
    brief_b = RapidFormEngine().review(sess_b)
    assert brief_a.session_overall == brief_b.session_overall
    assert [c.text for c in brief_a.cues] == [c.text for c in brief_b.cues]


def test_engine_custom_weights_shift_overall():
    sess = demo_session("squat", rep_count=3, asymmetry_severity=0.3)
    default = RapidFormEngine().review(sess).session_overall
    symmetry_only = RapidFormEngine(
        weights={"symmetry": 1.0, "depth": 0.0, "tempo": 0.0}
    ).review(sess).session_overall
    # Weighting all on symmetry should give a different (usually
    # lower, given asymmetry is the worst channel in this fixture)
    # overall.
    assert default != symmetry_only

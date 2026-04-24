"""Tests for the core dataclasses + claims guard."""

from __future__ import annotations

import pytest

from triage4_fit.core.models import (
    CoachBriefing,
    CoachCue,
    ExerciseSession,
    FormScore,
    JointPoseSample,
    RepObservation,
)


# ---------------------------------------------------------------------------
# JointPoseSample
# ---------------------------------------------------------------------------


def test_joint_pose_sample_normalised_range():
    s = JointPoseSample(joint="hip_l", x=0.5, y=0.5, confidence=0.9)
    assert s.x == 0.5


def test_joint_pose_sample_rejects_out_of_range():
    with pytest.raises(ValueError):
        JointPoseSample(joint="hip_l", x=1.5, y=0.5)
    with pytest.raises(ValueError):
        JointPoseSample(joint="hip_l", x=0.5, y=-0.1)
    with pytest.raises(ValueError):
        JointPoseSample(joint="hip_l", x=0.5, y=0.5, confidence=2.0)


# ---------------------------------------------------------------------------
# RepObservation
# ---------------------------------------------------------------------------


def test_rep_observation_minimal():
    r = RepObservation(rep_index=0, duration_s=2.5)
    assert r.rep_index == 0
    assert r.samples == []


def test_rep_observation_rejects_negative_index():
    with pytest.raises(ValueError):
        RepObservation(rep_index=-1, duration_s=2.0)


def test_rep_observation_rejects_zero_duration():
    with pytest.raises(ValueError):
        RepObservation(rep_index=0, duration_s=0)


def test_rep_observation_rejects_implausible_hr():
    with pytest.raises(ValueError):
        RepObservation(rep_index=0, duration_s=2.0, hr_bpm=300)


# ---------------------------------------------------------------------------
# ExerciseSession
# ---------------------------------------------------------------------------


def test_session_rejects_empty_trainee_id():
    with pytest.raises(ValueError):
        ExerciseSession(trainee_id="", exercise="squat")


def test_session_rejects_unknown_exercise():
    with pytest.raises(ValueError):
        ExerciseSession(trainee_id="t1", exercise="muscle-up")  # type: ignore[arg-type]


def test_session_rejects_rpe_out_of_range():
    with pytest.raises(ValueError):
        ExerciseSession(trainee_id="t1", exercise="squat", reported_rpe=11)


def test_session_rep_count():
    sess = ExerciseSession(
        trainee_id="t1",
        exercise="squat",
        reps=[RepObservation(rep_index=i, duration_s=2.0) for i in range(3)],
    )
    assert sess.rep_count == 3


# ---------------------------------------------------------------------------
# FormScore
# ---------------------------------------------------------------------------


def test_form_score_rejects_out_of_unit():
    with pytest.raises(ValueError):
        FormScore(rep_index=0, symmetry=1.2, depth=0.5, tempo=0.5, overall=0.7)


def test_form_score_stores_values():
    s = FormScore(rep_index=1, symmetry=0.9, depth=0.8, tempo=0.7, overall=0.85)
    assert s.rep_index == 1


# ---------------------------------------------------------------------------
# CoachCue — claims guard
# ---------------------------------------------------------------------------


def test_coach_cue_allows_wellness_text():
    cue = CoachCue(
        rep_index=0,
        kind="asymmetry",
        severity="minor",
        text="Left hip dropped — focus on even effort.",
    )
    assert cue.severity == "minor"


@pytest.mark.parametrize(
    "bad_text",
    [
        "You are injured, stop now.",
        "Diagnose the issue with your knee.",
        "This is a dangerous posture.",
        "Provides medical advice.",
    ],
)
def test_coach_cue_rejects_forbidden_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        CoachCue(rep_index=0, kind="asymmetry", severity="minor", text=bad_text)


def test_coach_cue_rejects_empty_text():
    with pytest.raises(ValueError):
        CoachCue(rep_index=0, kind="tempo", severity="minor", text="   ")


# ---------------------------------------------------------------------------
# CoachBriefing
# ---------------------------------------------------------------------------


def test_briefing_as_text_without_cues():
    sess = ExerciseSession(trainee_id="t1", exercise="squat")
    brief = CoachBriefing(session=sess, session_overall=0.92)
    text = brief.as_text()
    assert "t1" in text
    assert "consistent" in text.lower()


def test_briefing_cues_at_severity_filter():
    sess = ExerciseSession(trainee_id="t1", exercise="squat")
    brief = CoachBriefing(
        session=sess,
        cues=[
            CoachCue(rep_index=0, kind="asymmetry", severity="minor", text="a"),
            CoachCue(rep_index=1, kind="tempo", severity="severe", text="b"),
        ],
    )
    assert len(brief.cues_at_severity("severe")) == 1
    assert len(brief.cues_at_severity("minor")) == 1
    assert brief.cues_at_severity("severe")[0].kind == "tempo"

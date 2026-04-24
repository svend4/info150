"""Tests for the core dataclasses + triple claims guard."""

from __future__ import annotations

import pytest

from triage4_drive.core.models import (
    CanBusSample,
    DispatcherAlert,
    DriverObservation,
    DrivingSession,
    EyeStateSample,
    FatigueScore,
    GazeSample,
    PostureSample,
)


# ---------------------------------------------------------------------------
# EyeStateSample / GazeSample / PostureSample
# ---------------------------------------------------------------------------


def test_eye_sample_rejects_out_of_range_closure():
    with pytest.raises(ValueError):
        EyeStateSample(t_s=0.0, closure=1.5)


def test_eye_sample_rejects_negative_time():
    with pytest.raises(ValueError):
        EyeStateSample(t_s=-0.5, closure=0.5)


def test_gaze_sample_rejects_unknown_region():
    with pytest.raises(ValueError):
        GazeSample(t_s=0.0, region="space")  # type: ignore[arg-type]


def test_posture_sample_rejects_out_of_range():
    with pytest.raises(ValueError):
        PostureSample(t_s=0.0, nose_y=1.5, shoulder_midline_y=0.5)


def test_can_sample_rejects_implausible_speed():
    with pytest.raises(ValueError):
        CanBusSample(t_s=0.0, speed_kmh=500)


def test_can_sample_accepts_none_fields():
    c = CanBusSample(t_s=0.5)
    assert c.speed_kmh is None


# ---------------------------------------------------------------------------
# DriverObservation
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_session_id():
    with pytest.raises(ValueError):
        DriverObservation(session_id="", window_duration_s=10.0)


def test_observation_rejects_non_positive_duration():
    with pytest.raises(ValueError):
        DriverObservation(session_id="s", window_duration_s=0)


def test_observation_accepts_empty_sample_lists():
    obs = DriverObservation(session_id="s", window_duration_s=5.0)
    assert obs.eye_samples == []


# ---------------------------------------------------------------------------
# FatigueScore
# ---------------------------------------------------------------------------


def test_fatigue_score_rejects_out_of_unit():
    with pytest.raises(ValueError):
        FatigueScore(
            session_id="s",
            perclos=1.5, distraction=0.0, incapacitation=0.0,
            overall=0.5, alert_level="ok",
        )


def test_fatigue_score_rejects_unknown_level():
    with pytest.raises(ValueError):
        FatigueScore(
            session_id="s",
            perclos=0.1, distraction=0.1, incapacitation=0.1,
            overall=0.1, alert_level="urgent",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# DispatcherAlert — triple claims guard
# ---------------------------------------------------------------------------


def test_alert_allows_behavioural_text():
    alert = DispatcherAlert(
        session_id="s",
        kind="drowsiness",
        level="caution",
        text="PERCLOS 0.2. Consider a rest break.",
    )
    assert alert.level == "caution"


@pytest.mark.parametrize(
    "bad_text",
    [
        "Driver appears drunk.",
        "Possible stroke — escalate.",
        "Seizure detected.",
        "Heart attack in progress.",
        "Diagnose narcolepsy.",
        "Prescribe a rest break.",
        "Confirmed deceased at 14:22.",
        "Under the influence of alcohol.",
        "Driver has arrhythmia.",
    ],
)
def test_alert_rejects_clinical_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        DispatcherAlert(
            session_id="s",
            kind="drowsiness",
            level="critical",
            text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Auto-brake the vehicle.",
        "Stop the vehicle now.",
        "Pull over now — mandatory.",
        "Disengage autopilot.",
        "Take over from the driver.",
        "Apply brake immediately.",
        "Brake now.",
        "Accelerate to a safe speed.",
    ],
)
def test_alert_rejects_operational_command_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        DispatcherAlert(
            session_id="s",
            kind="drowsiness",
            level="critical",
            text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Same driver as last shift.",
        "Matches previous driver in our fleet.",
        "Driver identity confirmed.",
        "Biometric match found.",
        "Facial print on record.",
        "Identify the driver by face.",
        "Driver's face print archived.",
    ],
)
def test_alert_rejects_privacy_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        DispatcherAlert(
            session_id="s",
            kind="drowsiness",
            level="caution",
            text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Driver John shows PERCLOS 0.3 — check in.",
        "Driver Mary has drifted off-road.",
        "Driver Mike appears drowsy.",
    ],
)
def test_alert_rejects_identifier_patterns(bad_text: str):
    with pytest.raises(ValueError):
        DispatcherAlert(
            session_id="s",
            kind="drowsiness",
            level="caution",
            text=bad_text,
        )


def test_alert_rejects_empty_text():
    with pytest.raises(ValueError):
        DispatcherAlert(
            session_id="s",
            kind="drowsiness",
            level="caution",
            text="  ",
        )


def test_alert_rejects_unknown_kind():
    with pytest.raises(ValueError):
        DispatcherAlert(
            session_id="s",
            kind="celebration",  # type: ignore[arg-type]
            level="ok",
            text="Nice driving.",
        )


# ---------------------------------------------------------------------------
# DrivingSession
# ---------------------------------------------------------------------------


def test_session_rejects_empty_id():
    with pytest.raises(ValueError):
        DrivingSession(session_id="")


def test_session_window_count_and_latest():
    score_a = FatigueScore(
        session_id="s",
        perclos=0.1, distraction=0.0, incapacitation=0.0,
        overall=0.05, alert_level="ok",
    )
    score_b = FatigueScore(
        session_id="s",
        perclos=0.25, distraction=0.1, incapacitation=0.0,
        overall=0.15, alert_level="ok",
    )
    sess = DrivingSession(session_id="s", scores=[score_a, score_b])
    assert sess.window_count == 2
    assert sess.latest_overall() == 0.15


def test_session_alert_level_filter():
    alert_ok = DispatcherAlert(
        session_id="s", kind="drowsiness", level="caution",
        text="PERCLOS caution. Consider a rest break.",
    )
    alert_crit = DispatcherAlert(
        session_id="s", kind="incapacitation", level="critical",
        text="Postural-tone signature — dispatcher-in-the-loop required.",
    )
    sess = DrivingSession(session_id="s", alerts=[alert_ok, alert_crit])
    assert len(sess.alerts_at_level("critical")) == 1
    assert sess.alerts_at_level("critical")[0].kind == "incapacitation"


def test_session_as_text_without_alerts():
    sess = DrivingSession(session_id="s")
    text = sess.as_text()
    assert "s" in text
    assert "No caution" in text

"""Tests for the core dataclasses + quadruple claims guard."""

from __future__ import annotations

import pytest

from triage4_home.core.models import (
    ActivitySample,
    CaregiverAlert,
    HomeReport,
    ImpactSample,
    ResidentObservation,
    RoomTransition,
    WellnessScore,
)


# ---------------------------------------------------------------------------
# ImpactSample / ActivitySample / RoomTransition
# ---------------------------------------------------------------------------


def test_impact_sample_rejects_negative_magnitude():
    with pytest.raises(ValueError):
        ImpactSample(t_s=1.0, magnitude_g=-1.0, stillness_after_s=5.0)


def test_impact_sample_rejects_implausible_magnitude():
    with pytest.raises(ValueError):
        ImpactSample(t_s=1.0, magnitude_g=50.0, stillness_after_s=5.0)


def test_impact_sample_accepts_resting():
    s = ImpactSample(t_s=1.0, magnitude_g=1.0, stillness_after_s=0.0)
    assert s.stillness_after_s == 0.0


def test_activity_sample_rejects_unknown_intensity():
    with pytest.raises(ValueError):
        ActivitySample(t_s=1.0, intensity="sprinting")  # type: ignore[arg-type]


def test_room_transition_rejects_same_from_to():
    with pytest.raises(ValueError):
        RoomTransition(
            t_s=1.0, from_room="kitchen", to_room="kitchen",
            distance_m=3.0, duration_s=4.0,
        )


def test_room_transition_rejects_bad_distance():
    with pytest.raises(ValueError):
        RoomTransition(
            t_s=1.0, from_room="kitchen", to_room="living",
            distance_m=0.0, duration_s=4.0,
        )


def test_room_transition_rejects_bad_duration():
    with pytest.raises(ValueError):
        RoomTransition(
            t_s=1.0, from_room="kitchen", to_room="living",
            distance_m=4.0, duration_s=0.0,
        )


# ---------------------------------------------------------------------------
# ResidentObservation
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_window_id():
    with pytest.raises(ValueError):
        ResidentObservation(window_id="", window_duration_s=3600.0)


def test_observation_rejects_non_positive_duration():
    with pytest.raises(ValueError):
        ResidentObservation(window_id="d", window_duration_s=0)


# ---------------------------------------------------------------------------
# WellnessScore
# ---------------------------------------------------------------------------


def test_wellness_rejects_out_of_unit():
    with pytest.raises(ValueError):
        WellnessScore(
            window_id="w",
            fall_risk=1.5, activity_alignment=1.0,
            mobility_trend=1.0, overall=1.0, alert_level="ok",
        )


def test_wellness_rejects_unknown_level():
    with pytest.raises(ValueError):
        WellnessScore(
            window_id="w",
            fall_risk=0.1, activity_alignment=1.0,
            mobility_trend=1.0, overall=0.9,
            alert_level="critical",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# CaregiverAlert — quadruple claims guard
# ---------------------------------------------------------------------------


def test_alert_allows_observational_text():
    alert = CaregiverAlert(
        window_id="w",
        kind="activity",
        level="check_in",
        text="Resident activity pattern deviates from baseline. Consider a check-in call.",
    )
    assert alert.level == "check_in"


@pytest.mark.parametrize(
    "bad_text",
    [
        "Possible dementia onset.",
        "Alzheimer's-consistent pattern.",
        "Parkinson features observed.",
        "Cognitive decline is apparent.",
        "Likely dehydrated today.",
        "Possible infection.",
        "Diagnose early sepsis.",
        "Prescribe fluids.",
        "Administer medications.",
    ],
)
def test_alert_rejects_clinical_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        CaregiverAlert(
            window_id="w",
            kind="activity",
            level="urgent",
            text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Call 911 now.",
        "Dispatch ambulance.",
        "Call emergency services.",
        "Activate medical alarm.",
        "Contact the paramedic.",
    ],
)
def test_alert_rejects_operational_command_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        CaregiverAlert(
            window_id="w",
            kind="fall",
            level="urgent",
            text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Same resident as yesterday.",
        "Previous resident also showed this.",
        "Identify the resident via face.",
        "Biometric match found.",
        "Facial print matched.",
        "Voice print matched.",
    ],
)
def test_alert_rejects_privacy_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        CaregiverAlert(
            window_id="w",
            kind="activity",
            level="check_in",
            text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Resident John had an impact event.",
        "Resident Mary appears to have fallen.",
        "Resident Mike's activity dropped.",
    ],
)
def test_alert_rejects_identifier_patterns(bad_text: str):
    with pytest.raises(ValueError):
        CaregiverAlert(
            window_id="w",
            kind="activity",
            level="check_in",
            text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Resident appears confused.",
        "Resident disoriented this morning.",
        "Resident is incompetent.",
        "Resident cannot care for themselves.",
        "Dementia patient's activity dropped.",
        "Demented behaviour observed.",
        "Wandering in the kitchen.",
        "Resident is deteriorating.",
        "Senile activity pattern.",
        "Feeble today.",
        "Frail pace.",
    ],
)
def test_alert_rejects_dignity_vocabulary(bad_text: str):
    """The NEW boundary in this sibling. Pathologizing language
    rejected at construction time."""
    with pytest.raises(ValueError):
        CaregiverAlert(
            window_id="w",
            kind="activity",
            level="check_in",
            text=bad_text,
        )


def test_alert_rejects_empty_text():
    with pytest.raises(ValueError):
        CaregiverAlert(
            window_id="w",
            kind="activity",
            level="ok",
            text="   ",
        )


def test_alert_rejects_unknown_kind():
    with pytest.raises(ValueError):
        CaregiverAlert(
            window_id="w",
            kind="nutrition",  # type: ignore[arg-type]
            level="ok",
            text="Resident had lunch.",
        )


# ---------------------------------------------------------------------------
# HomeReport
# ---------------------------------------------------------------------------


def test_report_rejects_empty_residence_id():
    with pytest.raises(ValueError):
        HomeReport(residence_id="")


def test_report_filters_by_level():
    score = WellnessScore(
        window_id="w", fall_risk=0.0, activity_alignment=1.0,
        mobility_trend=1.0, overall=1.0, alert_level="ok",
    )
    alert_a = CaregiverAlert(
        window_id="w", kind="activity", level="check_in",
        text="Consider a check-in call.",
    )
    alert_b = CaregiverAlert(
        window_id="w", kind="fall", level="urgent",
        text="Impact event detected. Contact the resident.",
    )
    report = HomeReport(
        residence_id="R1", scores=[score], alerts=[alert_a, alert_b],
    )
    assert report.window_count == 1
    assert len(report.alerts_at_level("urgent")) == 1
    assert len(report.alerts_at_level("check_in")) == 1


def test_report_as_text_without_alerts():
    report = HomeReport(residence_id="R1")
    text = report.as_text()
    assert "R1" in text
    assert "No check-in" in text


def test_report_latest_overall_default():
    report = HomeReport(residence_id="R1")
    assert report.latest_overall() == 1.0

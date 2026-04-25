"""Tests for core dataclasses + three-audience guards."""

from __future__ import annotations

import pytest

from triage4_sport.core.models import (
    AthleteBaseline,
    AthleteObservation,
    CoachMessage,
    MovementSample,
    PerformanceAssessment,
    PhysicianAlert,
    RecoveryHRSample,
    SessionReport,
    TrainerNote,
    WorkloadSample,
)


# ---------------------------------------------------------------------------
# Sample types
# ---------------------------------------------------------------------------


def test_movement_sample_rejects_unknown_kind():
    with pytest.raises(ValueError):
        MovementSample(
            t_s=0.0,
            kind="dunk",  # type: ignore[arg-type]
            form_asymmetry=0.1, range_of_motion=0.9,
        )


def test_movement_sample_rejects_out_of_unit():
    with pytest.raises(ValueError):
        MovementSample(
            t_s=0.0, kind="kick",
            form_asymmetry=1.5, range_of_motion=0.9,
        )


def test_workload_sample_rejects_implausible_distance():
    with pytest.raises(ValueError):
        WorkloadSample(
            t_s=0.0, distance_m=50000,
            high_speed_runs=10, accelerations=10, decelerations=10,
        )


def test_recovery_sample_rejects_implausible_hr():
    with pytest.raises(ValueError):
        RecoveryHRSample(
            t_s=0.0, peak_hr_bpm=500.0, recovery_drop_bpm=20.0,
        )


def test_athlete_baseline_rejects_out_of_unit():
    with pytest.raises(ValueError):
        AthleteBaseline(
            typical_form_asymmetry=1.5,
            typical_workload_index=0.5,
            typical_recovery_drop_bpm=30,
        )


# ---------------------------------------------------------------------------
# AthleteObservation
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_token():
    with pytest.raises(ValueError):
        AthleteObservation(
            athlete_token="", sport="soccer",
            session_duration_s=3600.0,
        )


def test_observation_rejects_unknown_sport():
    with pytest.raises(ValueError):
        AthleteObservation(
            athlete_token="A", sport="darts",  # type: ignore[arg-type]
            session_duration_s=3600.0,
        )


def test_observation_rejects_bad_duration():
    with pytest.raises(ValueError):
        AthleteObservation(
            athlete_token="A", sport="soccer",
            session_duration_s=0,
        )


# ---------------------------------------------------------------------------
# PerformanceAssessment
# ---------------------------------------------------------------------------


def test_assessment_rejects_out_of_unit():
    with pytest.raises(ValueError):
        PerformanceAssessment(
            athlete_token="A",
            form_asymmetry_safety=1.5,
            workload_load_safety=1.0,
            recovery_hr_safety=1.0,
            baseline_deviation_safety=1.0,
            overall=1.0,
            risk_band="steady",
        )


def test_assessment_rejects_unknown_risk_band():
    with pytest.raises(ValueError):
        PerformanceAssessment(
            athlete_token="A",
            form_asymmetry_safety=1.0,
            workload_load_safety=1.0,
            recovery_hr_safety=1.0,
            baseline_deviation_safety=1.0,
            overall=1.0,
            risk_band="critical",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Universal guards (apply to all three audiences)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dataclass_obj", [CoachMessage, TrainerNote])
@pytest.mark.parametrize(
    "bad_text",
    [
        "Predicts injury within two weeks.",
        "Predict injury based on this pattern.",
        "Prevents injury via load management.",
        "Prevent injury through baseline tracking.",
        "Will get injured if continues.",
        "Injury imminent next session.",
        "Guaranteed safe to return.",
        "Ready to play tonight.",
        "Cleared to play next match.",
        "No injury risk in this session.",
    ],
)
def test_universal_injury_prediction_overreach(dataclass_obj, bad_text: str):
    with pytest.raises(ValueError, match="injury-prediction"):
        dataclass_obj(athlete_token="A", text=bad_text)


def test_physician_alert_universal_injury_prediction_overreach():
    with pytest.raises(ValueError, match="injury-prediction"):
        PhysicianAlert(
            athlete_token="A",
            text="Predicts injury within two weeks.",
            reasoning_trace="trace",
        )


@pytest.mark.parametrize("dataclass_obj", [CoachMessage, TrainerNote])
@pytest.mark.parametrize(
    "bad_text",
    [
        "Athlete John shows asymmetry.",
        "Athlete Maria has elevated load.",
        "Player Mike persistent imbalance.",
        "Player Chris poor recovery.",
    ],
)
def test_universal_athlete_identifier(dataclass_obj, bad_text: str):
    with pytest.raises(ValueError, match="identify"):
        dataclass_obj(athlete_token="A", text=bad_text)


@pytest.mark.parametrize("dataclass_obj", [CoachMessage, TrainerNote])
@pytest.mark.parametrize(
    "bad_text",
    [
        "Will be cut from roster.",
        "Roster decision pending.",
        "Will lose contract.",
        "Marketability impact attached.",
        "Marketability concern surfaced.",
        "Trade rumour circulating.",
        "Trade rumor escalating.",
    ],
)
def test_universal_career_jeopardy(dataclass_obj, bad_text: str):
    with pytest.raises(ValueError, match="career-jeopardy"):
        dataclass_obj(athlete_token="A", text=bad_text)


@pytest.mark.parametrize("dataclass_obj", [CoachMessage, TrainerNote])
@pytest.mark.parametrize(
    "bad_text",
    [
        "NFL data pattern attached.",
        "NBA tracking confirms it.",
        "EPL fixture data shows.",
        "Premier League records.",
        "Bundesliga match included.",
        "Serie A baseline differs.",
        "Champions League adjusted load.",
    ],
)
def test_universal_team_league_names(dataclass_obj, bad_text: str):
    with pytest.raises(ValueError, match="team / league name"):
        dataclass_obj(athlete_token="A", text=bad_text)


# ---------------------------------------------------------------------------
# CoachMessage strict guard
# ---------------------------------------------------------------------------


def test_coach_message_allows_form_text():
    m = CoachMessage(
        athlete_token="A",
        text="Form asymmetry trending above baseline. Trainer review recommended.",
    )
    assert m.text.startswith("Form")


@pytest.mark.parametrize(
    "bad_text",
    [
        "ACL tear visible in scan.",
        "MCL strain suspected.",
        "PCL involvement possible.",
        "LCL irritation seen.",
        "Rotator cuff impingement.",
        "Meniscus issue surfaced.",
        "Labrum involvement.",
        "Tendinitis probable.",
        "Tendonitis pattern.",
        "Concussion symptoms.",
        "Fracture indicated.",
        "Tear visible.",
        "Sprain noted.",
        "Strain injury pattern.",
        "Medical clearance pending.",
    ],
)
def test_coach_message_rejects_clinical_jargon(bad_text: str):
    with pytest.raises(ValueError, match="clinical jargon"):
        CoachMessage(athlete_token="A", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Athlete is injured this session.",
        "Has an injury that needs review.",
        "Confirmed injury found.",
        "Injury confirmed in scan.",
        "Out for the season likely.",
    ],
)
def test_coach_message_rejects_definitive_injury(bad_text: str):
    with pytest.raises(ValueError, match="definitive-injury"):
        CoachMessage(athlete_token="A", text=bad_text)


def test_coach_message_rejects_empty_text():
    with pytest.raises(ValueError):
        CoachMessage(athlete_token="A", text="   ")


# ---------------------------------------------------------------------------
# TrainerNote intermediate guard
# ---------------------------------------------------------------------------


def test_trainer_note_allows_rom_vocabulary():
    """Critical property — TrainerNote PERMITS vocabulary
    that CoachMessage rejects."""
    n = TrainerNote(
        athlete_token="A",
        text="Range of motion 0.8; quadriceps fatigue level rising. RPE 7.",
    )
    assert "range of motion" in n.text.lower()


def test_trainer_note_allows_acute_load_vocabulary():
    n = TrainerNote(
        athlete_token="A",
        text="Acute load above chronic load index — monitor next session.",
    )
    assert "acute load" in n.text.lower()


@pytest.mark.parametrize(
    "bad_text",
    [
        "Tear visible in scan.",
        "Fracture confirmed.",
        "Confirmed diagnosis: tendinitis.",
        "Diagnosis: fracture.",
        "Diagnosis is patellar tendinitis.",
    ],
)
def test_trainer_note_rejects_definitive_diagnosis(bad_text: str):
    with pytest.raises(ValueError, match="definitive-diagnosis"):
        TrainerNote(athlete_token="A", text=bad_text)


# ---------------------------------------------------------------------------
# PhysicianAlert permissive + positive requirement
# ---------------------------------------------------------------------------


def test_physician_alert_allows_clinical_observation():
    """Critical property — PhysicianAlert PERMITS clinical
    observation vocabulary."""
    a = PhysicianAlert(
        athlete_token="A",
        text="Right-leg gait asymmetry persisting; flexion deficit observed; quadriceps fatigue elevated.",
        reasoning_trace="form_asymmetry@1.0.0 → 0.42",
    )
    assert "gait asymmetry" in a.text.lower()


def test_physician_alert_requires_reasoning_trace():
    """Positive requirement — copied from triage4-clinic
    pattern."""
    with pytest.raises(ValueError, match="reasoning_trace"):
        PhysicianAlert(
            athlete_token="A",
            text="Gait asymmetry observed.",
            reasoning_trace="   ",
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Diagnosis: ACL tear.",
        "Diagnosis is patellofemoral.",
        "Confirmed diagnosis attached.",
        "The athlete has a fracture.",
        "The athlete has an ACL tear.",
        "The athlete has a meniscus tear.",
    ],
)
def test_physician_alert_rejects_definitive_diagnosis(bad_text: str):
    with pytest.raises(ValueError, match="definitive-diagnosis"):
        PhysicianAlert(
            athlete_token="A", text=bad_text,
            reasoning_trace="trace",
        )


# ---------------------------------------------------------------------------
# Cross-audience: each guard has its OWN behavior
# ---------------------------------------------------------------------------


def test_clinical_jargon_blocked_in_coach_allowed_in_trainer():
    """ROM vocabulary: blocked in coach (it's clinical-ish),
    allowed in trainer."""
    # 'fatigue level' permitted in trainer.
    TrainerNote(
        athlete_token="A",
        text="Fatigue level rising; RPE 8 last interval.",
    )
    # And explicitly: ROM passes trainer.
    TrainerNote(
        athlete_token="A",
        text="Range of motion 0.8 in left hip.",
    )
    # In coach, ROM not blocked specifically (the coach
    # blocklist focuses on injury jargon), but "tendinitis"
    # IS blocked in coach.
    with pytest.raises(ValueError):
        CoachMessage(
            athlete_token="A",
            text="Tendinitis pattern observed today.",
        )
    # And the same "tendinitis" is also blocked in trainer
    # via the universal definitive-diagnosis lists if
    # phrased as "diagnosis: tendinitis":
    with pytest.raises(ValueError):
        TrainerNote(
            athlete_token="A",
            text="Diagnosis: tendinitis observed today.",
        )


# ---------------------------------------------------------------------------
# SessionReport
# ---------------------------------------------------------------------------


def test_report_rejects_empty_token():
    a = PerformanceAssessment(
        athlete_token="A",
        form_asymmetry_safety=1.0,
        workload_load_safety=1.0,
        recovery_hr_safety=1.0,
        baseline_deviation_safety=1.0,
        overall=1.0, risk_band="steady",
    )
    with pytest.raises(ValueError):
        SessionReport(athlete_token="", assessment=a)


def test_report_alerts_count_combines_all_streams():
    a = PerformanceAssessment(
        athlete_token="A",
        form_asymmetry_safety=0.4,
        workload_load_safety=0.4,
        recovery_hr_safety=0.4,
        baseline_deviation_safety=0.4,
        overall=0.4, risk_band="hold",
    )
    coach = CoachMessage(
        athlete_token="A",
        text="Form patterns deviating from athlete baseline.",
    )
    trainer = TrainerNote(
        athlete_token="A",
        text="Acute load above chronic load.",
    )
    physician = PhysicianAlert(
        athlete_token="A",
        text="Multi-channel deviation; gait asymmetry, fatigue elevated.",
        reasoning_trace="form_asymmetry@1.0.0 → 0.20.",
    )
    report = SessionReport(
        athlete_token="A", assessment=a,
        coach_messages=[coach], trainer_notes=[trainer],
        physician_alert=physician,
    )
    assert report.alerts_count() == 3


def test_report_as_text_no_alerts_is_observation_worded():
    a = PerformanceAssessment(
        athlete_token="A",
        form_asymmetry_safety=1.0,
        workload_load_safety=1.0,
        recovery_hr_safety=1.0,
        baseline_deviation_safety=1.0,
        overall=1.0, risk_band="steady",
    )
    report = SessionReport(athlete_token="A", assessment=a)
    text = report.as_text().lower()
    assert "no alerts" in text
    assert "remains required" in text

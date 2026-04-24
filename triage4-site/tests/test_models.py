"""Tests for the core dataclasses + 5-boundary claims guard."""

from __future__ import annotations

import pytest

from triage4_site.core.models import (
    FatigueGaitSample,
    LiftingSample,
    PPESample,
    SafetyOfficerAlert,
    SafetyScore,
    SiteReport,
    ThermalSample,
    WorkerObservation,
)


# ---------------------------------------------------------------------------
# Sample types
# ---------------------------------------------------------------------------


def test_ppe_sample_accepts_empty_items():
    s = PPESample(t_s=0.0, items_detected=())
    assert s.items_detected == ()


def test_ppe_sample_rejects_duplicate_items():
    with pytest.raises(ValueError):
        PPESample(t_s=0.0, items_detected=("hard_hat", "hard_hat"))


def test_ppe_sample_rejects_unknown_item():
    with pytest.raises(ValueError):
        PPESample(t_s=0.0, items_detected=("umbrella",))  # type: ignore[arg-type]


def test_lifting_sample_rejects_implausible_angle():
    with pytest.raises(ValueError):
        LiftingSample(t_s=1.0, back_angle_deg=200.0, load_kg=10.0)


def test_lifting_sample_rejects_huge_load():
    with pytest.raises(ValueError):
        LiftingSample(t_s=1.0, back_angle_deg=30.0, load_kg=5000.0)


def test_thermal_sample_rejects_implausible_skin_temp():
    with pytest.raises(ValueError):
        ThermalSample(t_s=1.0, skin_temp_c=50.0, ambient_temp_c=20.0)


def test_thermal_sample_rejects_implausible_ambient():
    with pytest.raises(ValueError):
        ThermalSample(t_s=1.0, skin_temp_c=36.0, ambient_temp_c=-50.0)


def test_gait_sample_rejects_out_of_range_asymmetry():
    with pytest.raises(ValueError):
        FatigueGaitSample(t_s=1.0, pace_mps=1.0, asymmetry=1.5)


# ---------------------------------------------------------------------------
# WorkerObservation
# ---------------------------------------------------------------------------


def test_worker_observation_rejects_empty_token():
    with pytest.raises(ValueError):
        WorkerObservation(worker_token="", window_duration_s=3600.0)


def test_worker_observation_rejects_bad_condition():
    with pytest.raises(ValueError):
        WorkerObservation(
            worker_token="w", window_duration_s=10.0,
            site_condition="foggy",  # type: ignore[arg-type]
        )


def test_worker_observation_rejects_bad_required_ppe():
    with pytest.raises(ValueError):
        WorkerObservation(
            worker_token="w", window_duration_s=10.0,
            required_ppe=("umbrella",),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# SafetyScore
# ---------------------------------------------------------------------------


def test_safety_score_rejects_out_of_unit():
    with pytest.raises(ValueError):
        SafetyScore(
            worker_token="w",
            ppe_compliance=1.5, lifting_safety=0.5,
            heat_safety=0.5, fatigue_safety=0.5,
            overall=0.8, alert_level="ok",
        )


def test_safety_score_rejects_unknown_level():
    with pytest.raises(ValueError):
        SafetyScore(
            worker_token="w",
            ppe_compliance=1.0, lifting_safety=1.0,
            heat_safety=1.0, fatigue_safety=1.0,
            overall=1.0, alert_level="critical",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# SafetyOfficerAlert — 5-boundary claims guard
# ---------------------------------------------------------------------------


def test_alert_allows_observational_text():
    alert = SafetyOfficerAlert(
        worker_token="w",
        kind="ppe", level="watch",
        text="Zone 3: three PPE harness gaps in the last hour. Safety officer: consider a tailgate briefing.",
    )
    assert alert.level == "watch"


@pytest.mark.parametrize(
    "bad_text",
    [
        "Diagnose heat stroke.",
        "Worker is dehydrated.",
        "Possible musculoskeletal injury.",
        "Worker appears exhausted.",
        "Likely back injury.",
        "Pronounced deceased.",
    ],
)
def test_alert_rejects_clinical_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        SafetyOfficerAlert(
            worker_token="w", kind="heat", level="urgent", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Stop work on east roof.",
        "Shut down the site immediately.",
        "Halt operations in zone 3.",
        "Evacuate the north wing.",
        "Send worker home now.",
        "Call 911 at once.",
        "Dispatch ambulance.",
        "Call emergency services.",
    ],
)
def test_alert_rejects_operational_command_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        SafetyOfficerAlert(
            worker_token="w", kind="ppe", level="urgent", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Same worker as yesterday.",
        "Previous worker also violated PPE.",
        "Identify the worker via face.",
        "Biometric match found for this person.",
        "Facial print matched.",
    ],
)
def test_alert_rejects_privacy_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        SafetyOfficerAlert(
            worker_token="w", kind="ppe", level="watch", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Worker John missed harness.",
        "Worker Mary unsafe lift.",
        "Worker Mike repeated violations.",
    ],
)
def test_alert_rejects_identifier_patterns(bad_text: str):
    with pytest.raises(ValueError):
        SafetyOfficerAlert(
            worker_token="w", kind="ppe", level="watch", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Careless worker on east roof.",
        "Negligent PPE compliance.",
        "Lazy pace all shift.",
        "Reckless lifting pattern.",
        "Incompetent posture.",
        "Unfit for this role.",
        "Unprofessional safety record.",
    ],
)
def test_alert_rejects_dignity_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        SafetyOfficerAlert(
            worker_token="w", kind="ppe", level="watch", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Low productivity observed today.",
        "Performance metric dropped this week.",
        "Performance review indicates issues.",
        "Consider discipline for these lapses.",
        "Reprimand recommended.",
        "Write-up for repeat violations.",
        "HR action required.",
        "HR notification sent.",
        "Recommend termination.",
        "Fire the worker.",
        "Dismiss the worker for cause.",
        "Add to performance improvement plan.",
        "Withholding bonus this cycle.",
        "Apply incentive penalty.",
        "Schedule penalty warranted.",
    ],
)
def test_alert_rejects_labor_relations_vocabulary(bad_text: str):
    """The NEW boundary in this sibling. Every phrase that
    routes the signal into the HR / labor-discipline pipeline
    is rejected at construction time."""
    with pytest.raises(ValueError):
        SafetyOfficerAlert(
            worker_token="w", kind="ppe", level="watch", text=bad_text,
        )


def test_alert_rejects_empty_text():
    with pytest.raises(ValueError):
        SafetyOfficerAlert(
            worker_token="w", kind="ppe", level="ok", text="  ",
        )


def test_alert_rejects_unknown_kind():
    with pytest.raises(ValueError):
        SafetyOfficerAlert(
            worker_token="w", kind="attendance",  # type: ignore[arg-type]
            level="watch", text="Some text.",
        )


# ---------------------------------------------------------------------------
# SiteReport
# ---------------------------------------------------------------------------


def test_site_report_rejects_empty_id():
    with pytest.raises(ValueError):
        SiteReport(site_id="")


def test_site_report_filters_by_level_and_kind():
    alert_a = SafetyOfficerAlert(
        worker_token="w1", kind="ppe", level="watch",
        text="PPE below comfort band. Safety officer: keep an eye.",
    )
    alert_b = SafetyOfficerAlert(
        worker_token="w2", kind="heat", level="urgent",
        text="Marked heat signature. Safety officer: arrange cooling break.",
    )
    report = SiteReport(site_id="S1", alerts=[alert_a, alert_b])
    assert len(report.alerts_at_level("urgent")) == 1
    assert report.alerts_at_level("urgent")[0].kind == "heat"
    assert len(report.alerts_of_kind("ppe")) == 1


def test_site_report_as_text_without_alerts():
    report = SiteReport(site_id="S1")
    text = report.as_text()
    assert "S1" in text
    assert "No watch" in text

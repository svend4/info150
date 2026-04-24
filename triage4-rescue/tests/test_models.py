"""Tests for the core dataclasses + dual claims guard."""

from __future__ import annotations

import pytest

from triage4_rescue.core.models import (
    CivilianCasualty,
    IncidentReport,
    ResponderCue,
    TriageAssessment,
    VitalSignsObservation,
)


# ---------------------------------------------------------------------------
# VitalSignsObservation
# ---------------------------------------------------------------------------


def test_vitals_defaults_all_none():
    v = VitalSignsObservation()
    assert v.can_walk is None
    assert v.respiratory_bpm is None
    assert v.airway_repositioned is False


def test_vitals_rejects_implausible_respiratory():
    with pytest.raises(ValueError):
        VitalSignsObservation(respiratory_bpm=250)


def test_vitals_rejects_implausible_cap_refill():
    with pytest.raises(ValueError):
        VitalSignsObservation(capillary_refill_s=60)


def test_vitals_accepts_zero_respiratory():
    # Zero is legal — it means apneic.
    v = VitalSignsObservation(respiratory_bpm=0)
    assert v.respiratory_bpm == 0


# ---------------------------------------------------------------------------
# CivilianCasualty
# ---------------------------------------------------------------------------


def test_casualty_rejects_empty_id():
    with pytest.raises(ValueError):
        CivilianCasualty(casualty_id="", age_years=30)


def test_casualty_rejects_implausible_age():
    with pytest.raises(ValueError):
        CivilianCasualty(casualty_id="C1", age_years=200)


def test_casualty_age_group_adult():
    c = CivilianCasualty(casualty_id="C1", age_years=30)
    assert c.age_group == "adult"


def test_casualty_age_group_pediatric():
    c = CivilianCasualty(casualty_id="C1", age_years=5)
    assert c.age_group == "pediatric"


def test_casualty_age_group_unknown_defaults_to_adult():
    c = CivilianCasualty(casualty_id="C1")
    assert c.age_group == "adult"


def test_casualty_boundary_8_years_is_adult():
    # JumpSTART cutoff: < 8 is pediatric. Exactly 8 is adult.
    c = CivilianCasualty(casualty_id="C1", age_years=8)
    assert c.age_group == "adult"


# ---------------------------------------------------------------------------
# TriageAssessment
# ---------------------------------------------------------------------------


def test_assessment_rejects_unknown_tag():
    with pytest.raises(ValueError):
        TriageAssessment(
            casualty_id="C1",
            tag="red",  # type: ignore[arg-type]
            age_group="adult",
            reasoning="test",
        )


def test_assessment_rejects_empty_reasoning():
    with pytest.raises(ValueError):
        TriageAssessment(
            casualty_id="C1",
            tag="immediate",
            age_group="adult",
            reasoning="   ",
        )


def test_assessment_rejects_unknown_age_group():
    with pytest.raises(ValueError):
        TriageAssessment(
            casualty_id="C1",
            tag="delayed",
            age_group="toddler",  # type: ignore[arg-type]
            reasoning="test",
        )


# ---------------------------------------------------------------------------
# ResponderCue — dual claims guard
# ---------------------------------------------------------------------------


def test_cue_allows_advisory_text():
    cue = ResponderCue(
        casualty_id="C1",
        kind="breathing",
        severity="flag",
        text="Casualty C1 respiratory rate 34/min. START immediate.",
    )
    assert cue.severity == "flag"


@pytest.mark.parametrize(
    "bad_text",
    [
        "Patient has been pronounced deceased.",
        "Casualty is confirmed deceased.",
        "Diagnose head injury.",
        "Prescribe 500 mg ibuprofen.",
        "Administer fluids now.",
        "Cause of death is clear.",
    ],
)
def test_cue_rejects_clinical_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        ResponderCue(
            casualty_id="C1",
            kind="breathing",
            severity="flag",
            text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Deploy medics to north wing.",
        "Dispatch ambulance immediately.",
        "Assign team Alpha to this sector.",
        "Evacuate the building now.",
        "Transport to County General Hospital.",
        "Establish perimeter around debris.",
        "Clear the scene of bystanders.",
    ],
)
def test_cue_rejects_operational_command_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        ResponderCue(
            casualty_id="C1",
            kind="breathing",
            severity="advisory",
            text=bad_text,
        )


def test_cue_rejects_empty_text():
    with pytest.raises(ValueError):
        ResponderCue(
            casualty_id="C1",
            kind="ambulation",
            severity="info",
            text="   ",
        )


def test_cue_rejects_unknown_kind():
    with pytest.raises(ValueError):
        ResponderCue(
            casualty_id="C1",
            kind="vibes",  # type: ignore[arg-type]
            severity="info",
            text="Some text.",
        )


def test_cue_rejects_unknown_severity():
    with pytest.raises(ValueError):
        ResponderCue(
            casualty_id="C1",
            kind="ambulation",
            severity="urgent",  # type: ignore[arg-type]
            text="Some text.",
        )


# ---------------------------------------------------------------------------
# IncidentReport
# ---------------------------------------------------------------------------


def test_report_rejects_empty_incident_id():
    with pytest.raises(ValueError):
        IncidentReport(incident_id="")


def test_report_counts_tags():
    report = IncidentReport(
        incident_id="I1",
        assessments=[
            TriageAssessment(
                casualty_id=f"C{i}",
                tag=tag,  # type: ignore[arg-type]
                age_group="adult",
                reasoning="test",
            )
            for i, tag in enumerate(
                ["immediate", "immediate", "delayed", "minor", "deceased"]
            )
        ],
    )
    assert report.casualty_count == 5
    assert len(report.assessments_with_tag("immediate")) == 2
    assert len(report.assessments_with_tag("minor")) == 1


def test_report_as_text_mentions_counts():
    report = IncidentReport(
        incident_id="I1",
        assessments=[
            TriageAssessment(
                casualty_id="C1",
                tag="immediate",
                age_group="adult",
                reasoning="r",
            ),
        ],
    )
    text = report.as_text()
    assert "I1" in text
    assert "immediate: 1" in text


def test_report_flags_secondary_review_count():
    report = IncidentReport(
        incident_id="I1",
        assessments=[
            TriageAssessment(
                casualty_id="C1",
                tag="delayed",
                age_group="adult",
                reasoning="r",
                flag_for_secondary_review=True,
            ),
        ],
    )
    text = report.as_text()
    assert "flagged for secondary review" in text

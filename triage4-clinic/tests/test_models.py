"""Tests for the core dataclasses + grounded-alternatives + claims guard."""

from __future__ import annotations

import pytest

from triage4_clinic.core.models import (
    AcousticSample,
    AlternativeExplanation,
    ChannelReading,
    ClinicianAlert,
    CoughSample,
    PatientObservation,
    PatientSelfReport,
    PostureSample,
    PreTriageAssessment,
    PreTriageReport,
    VitalsSample,
)


# ---------------------------------------------------------------------------
# Raw samples
# ---------------------------------------------------------------------------


def test_vitals_sample_rejects_implausible_hr():
    with pytest.raises(ValueError):
        VitalsSample(t_s=0.0, hr_bpm=500, rr_bpm=18, reliable=True)


def test_vitals_sample_rejects_implausible_rr():
    with pytest.raises(ValueError):
        VitalsSample(t_s=0.0, hr_bpm=72, rr_bpm=200, reliable=True)


def test_acoustic_sample_rejects_out_of_unit():
    with pytest.raises(ValueError):
        AcousticSample(t_s=0.0, strain_score=1.5, clarity=0.9)


def test_cough_sample_rejects_out_of_unit_confidence():
    with pytest.raises(ValueError):
        CoughSample(t_s=0.0, confidence=1.5)


def test_posture_sample_rejects_out_of_unit():
    with pytest.raises(ValueError):
        PostureSample(t_s=0.0, sway_magnitude=1.5, balance_steadiness=0.9)


# ---------------------------------------------------------------------------
# PatientSelfReport
# ---------------------------------------------------------------------------


def test_self_report_as_list_empty():
    sr = PatientSelfReport()
    assert sr.as_list() == []


def test_self_report_as_list_with_flags():
    sr = PatientSelfReport(
        reports_chest_pain=True,
        reports_fever=True,
    )
    tokens = sr.as_list()
    assert "chest discomfort" in tokens
    assert "fever" in tokens
    assert len(tokens) == 2


# ---------------------------------------------------------------------------
# PatientObservation
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_token():
    with pytest.raises(ValueError):
        PatientObservation(patient_token="", window_duration_s=60.0)


def test_observation_rejects_bad_duration():
    with pytest.raises(ValueError):
        PatientObservation(patient_token="P", window_duration_s=0)


def test_observation_rejects_bad_age():
    with pytest.raises(ValueError):
        PatientObservation(
            patient_token="P", window_duration_s=60.0, age_years=200,
        )


def test_observation_rejects_bad_capture_quality():
    with pytest.raises(ValueError):
        PatientObservation(
            patient_token="P", window_duration_s=60.0,
            capture_quality="excellent",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# ChannelReading
# ---------------------------------------------------------------------------


def test_channel_reading_rejects_empty_signature_version():
    """Audit requirement — the exact signature code that
    produced a reading must be identifiable in the output."""
    with pytest.raises(ValueError):
        ChannelReading(channel="cardiac", value=0.5, signature_version="")


def test_channel_reading_rejects_whitespace_signature_version():
    with pytest.raises(ValueError):
        ChannelReading(channel="cardiac", value=0.5, signature_version="   ")


def test_channel_reading_rejects_out_of_unit_value():
    with pytest.raises(ValueError):
        ChannelReading(
            channel="cardiac", value=1.5, signature_version="v1",
        )


def test_channel_reading_rejects_unknown_channel():
    with pytest.raises(ValueError):
        ChannelReading(
            channel="weather",  # type: ignore[arg-type]
            value=0.5, signature_version="v1",
        )


# ---------------------------------------------------------------------------
# AlternativeExplanation
# ---------------------------------------------------------------------------


def test_alternative_explanation_allows_mechanism_text():
    alt = AlternativeExplanation(
        text="Could reflect recent physical exertion.",
        likelihood="plausible",
    )
    assert alt.likelihood == "plausible"


def test_alternative_explanation_rejects_empty_text():
    with pytest.raises(ValueError):
        AlternativeExplanation(text="", likelihood="plausible")


def test_alternative_explanation_rejects_unknown_likelihood():
    with pytest.raises(ValueError):
        AlternativeExplanation(
            text="Could reflect exertion.",
            likelihood="certain",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Diagnosis: cardiac anxiety.",
        "The patient has tachycardia.",
        "Confirms a respiratory infection.",
        "Is a case of panic disorder.",
    ],
)
def test_alternative_explanation_rejects_diagnostic_tokens(bad_text: str):
    """Secondary guard — the alternatives themselves cannot
    sneak a diagnostic label past the clinician."""
    with pytest.raises(ValueError):
        AlternativeExplanation(text=bad_text, likelihood="plausible")


# ---------------------------------------------------------------------------
# ClinicianAlert — positive + negative guards
# ---------------------------------------------------------------------------


def _valid_alt() -> AlternativeExplanation:
    return AlternativeExplanation(
        text="Could reflect recent physical exertion.",
        likelihood="plausible",
    )


def test_clinician_alert_valid_construction():
    a = ClinicianAlert(
        patient_token="P",
        channel="cardiac", recommendation="schedule",
        text="HR readings elevated; grounded alternatives follow.",
        alternative_explanations=(_valid_alt(),),
        reasoning_trace="cardiac_readings@1.0.0 → median HR > band_upper.",
    )
    assert a.channel == "cardiac"
    assert len(a.alternative_explanations) == 1


def test_clinician_alert_requires_non_empty_alternatives():
    """Positive requirement — THIS is the architectural
    contribution of this sibling."""
    with pytest.raises(ValueError, match="AlternativeExplanation"):
        ClinicianAlert(
            patient_token="P",
            channel="cardiac", recommendation="schedule",
            text="HR readings elevated.",
            alternative_explanations=(),
            reasoning_trace="trace",
        )


def test_clinician_alert_requires_non_empty_reasoning_trace():
    """Audit requirement — every alert must cite the signature
    + threshold that drove it."""
    with pytest.raises(ValueError, match="reasoning_trace"):
        ClinicianAlert(
            patient_token="P",
            channel="cardiac", recommendation="schedule",
            text="HR readings elevated.",
            alternative_explanations=(_valid_alt(),),
            reasoning_trace="   ",
        )


def test_clinician_alert_rejects_empty_text():
    with pytest.raises(ValueError):
        ClinicianAlert(
            patient_token="P",
            channel="cardiac", recommendation="schedule",
            text="   ",
            alternative_explanations=(_valid_alt(),),
            reasoning_trace="trace",
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Diagnosis of tachycardia.",
        "Diagnosis: panic disorder.",
        "Confirmed diagnosis in readings.",
        "The patient has cardiac disease.",
        "Is a case of acute anxiety.",
        "Confirms a respiratory infection.",
        "Diagnosis is straightforward.",
    ],
)
def test_clinician_alert_rejects_definitive_diagnosis(bad_text: str):
    with pytest.raises(ValueError):
        ClinicianAlert(
            patient_token="P",
            channel="cardiac", recommendation="schedule",
            text=bad_text,
            alternative_explanations=(_valid_alt(),),
            reasoning_trace="trace",
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Prescribe beta blocker.",
        "Already prescribed this week.",
        "Administer oxygen.",
        "Start medication before consult.",
        "Take this drug twice daily.",
        "Treatment: rest and fluids.",
    ],
)
def test_clinician_alert_rejects_treatment(bad_text: str):
    with pytest.raises(ValueError):
        ClinicianAlert(
            patient_token="P",
            channel="cardiac", recommendation="schedule",
            text=bad_text,
            alternative_explanations=(_valid_alt(),),
            reasoning_trace="trace",
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "FDA-cleared readings show elevation.",
        "FDA cleared signal analysis.",
        "This medical device flags the issue.",
        "SaMD-certified flag.",
        "Clinically validated elevated readings.",
        "The library diagnoses HR elevation.",
        "This replaces clinician review.",
        "Replaces the clinician in first-contact.",
    ],
)
def test_clinician_alert_rejects_regulatory_overclaim(bad_text: str):
    """The library must not pretend to be what it isn't."""
    with pytest.raises(ValueError):
        ClinicianAlert(
            patient_token="P",
            channel="cardiac", recommendation="schedule",
            text=bad_text,
            alternative_explanations=(_valid_alt(),),
            reasoning_trace="trace",
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "You are fine — no review needed.",
        "No need for review after this cycle.",
        "Can skip the visit.",
        "No clinical concerns flagged.",
        "All vital signs normal in this pass.",
        "Nothing unusual observed.",
    ],
)
def test_clinician_alert_rejects_reassurance(bad_text: str):
    with pytest.raises(ValueError):
        ClinicianAlert(
            patient_token="P",
            channel="cardiac", recommendation="schedule",
            text=bad_text,
            alternative_explanations=(_valid_alt(),),
            reasoning_trace="trace",
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Patient John shows elevated HR.",
        "Patient Mary has tachypnea readings.",
        "Patient Mike displays postural instability.",
    ],
)
def test_clinician_alert_rejects_patient_identifier(bad_text: str):
    with pytest.raises(ValueError):
        ClinicianAlert(
            patient_token="P",
            channel="cardiac", recommendation="schedule",
            text=bad_text,
            alternative_explanations=(_valid_alt(),),
            reasoning_trace="trace",
        )


def test_clinician_alert_rejects_unknown_channel():
    with pytest.raises(ValueError):
        ClinicianAlert(
            patient_token="P",
            channel="weather",  # type: ignore[arg-type]
            recommendation="schedule",
            text="HR readings elevated.",
            alternative_explanations=(_valid_alt(),),
            reasoning_trace="trace",
        )


def test_clinician_alert_rejects_unknown_recommendation():
    with pytest.raises(ValueError):
        ClinicianAlert(
            patient_token="P",
            channel="cardiac",
            recommendation="emergency",  # type: ignore[arg-type]
            text="HR readings elevated.",
            alternative_explanations=(_valid_alt(),),
            reasoning_trace="trace",
        )


# ---------------------------------------------------------------------------
# PreTriageAssessment + PreTriageReport
# ---------------------------------------------------------------------------


def test_assessment_rejects_out_of_unit():
    with pytest.raises(ValueError):
        PreTriageAssessment(
            patient_token="P",
            cardiac_safety=1.5, respiratory_safety=1.0,
            acoustic_safety=1.0, postural_safety=1.0,
            overall=1.0, recommendation="schedule",
        )


def test_assessment_rejects_unknown_recommendation():
    with pytest.raises(ValueError):
        PreTriageAssessment(
            patient_token="P",
            cardiac_safety=1.0, respiratory_safety=1.0,
            acoustic_safety=1.0, postural_safety=1.0,
            overall=1.0, recommendation="emergency",  # type: ignore[arg-type]
        )


def test_report_rejects_empty_token():
    a = PreTriageAssessment(
        patient_token="P",
        cardiac_safety=1.0, respiratory_safety=1.0,
        acoustic_safety=1.0, postural_safety=1.0,
        overall=1.0, recommendation="schedule",
    )
    with pytest.raises(ValueError):
        PreTriageReport(patient_token="", assessment=a)


def test_report_as_text_no_alerts_is_not_reassuring():
    """Property test — absence of alerts must NOT produce
    reassurance text. Must explicitly say 'not a clearance
    of the patient'."""
    a = PreTriageAssessment(
        patient_token="P",
        cardiac_safety=1.0, respiratory_safety=1.0,
        acoustic_safety=1.0, postural_safety=1.0,
        overall=1.0, recommendation="self_care",
    )
    report = PreTriageReport(patient_token="P", assessment=a)
    text = report.as_text().lower()
    assert "not a clearance" in text
    # And does not contain any of the reassurance phrases
    # that would be rejected if emitted through a
    # ClinicianAlert.
    for phrase in (
        "you are fine",
        "no need for review",
        "can skip the visit",
        "no clinical concerns",
        "all vital signs normal",
        "nothing unusual",
    ):
        assert phrase not in text


def test_report_filters_by_recommendation():
    alt = AlternativeExplanation(
        text="Could reflect exertion.", likelihood="plausible",
    )
    a1 = ClinicianAlert(
        patient_token="P", channel="cardiac", recommendation="schedule",
        text="Cardiac readings elevated.",
        alternative_explanations=(alt,),
        reasoning_trace="cardiac v1 → elevated.",
    )
    a2 = ClinicianAlert(
        patient_token="P", channel="respiratory",
        recommendation="urgent_review",
        text="Respiratory readings markedly elevated.",
        alternative_explanations=(alt,),
        reasoning_trace="respiratory v1 → markedly elevated.",
    )
    assessment = PreTriageAssessment(
        patient_token="P",
        cardiac_safety=0.5, respiratory_safety=0.3,
        acoustic_safety=1.0, postural_safety=1.0,
        overall=0.5, recommendation="urgent_review",
    )
    report = PreTriageReport(
        patient_token="P", assessment=assessment, alerts=[a1, a2],
    )
    assert len(report.alerts_for_recommendation("urgent_review")) == 1
    assert report.alerts_for_recommendation("urgent_review")[0].channel == "respiratory"

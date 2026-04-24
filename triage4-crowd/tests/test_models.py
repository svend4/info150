"""Tests for the core dataclasses + six-boundary claims guard."""

from __future__ import annotations

import pytest

from triage4_crowd.core.models import (
    CrowdScore,
    DensityReading,
    FlowSample,
    MedicalCandidate,
    PressureReading,
    VenueOpsAlert,
    VenueReport,
    ZoneObservation,
)


# ---------------------------------------------------------------------------
# Raw readings
# ---------------------------------------------------------------------------


def test_density_reading_rejects_implausible():
    with pytest.raises(ValueError):
        DensityReading(t_s=0.0, persons_per_m2=50.0)


def test_density_reading_rejects_negative_time():
    with pytest.raises(ValueError):
        DensityReading(t_s=-1.0, persons_per_m2=2.0)


def test_flow_sample_rejects_unknown_direction():
    with pytest.raises(ValueError):
        FlowSample(
            t_s=0, net_direction="sideways",  # type: ignore[arg-type]
            magnitude=0.5, compaction=0.5,
        )


def test_flow_sample_rejects_out_of_unit_magnitude():
    with pytest.raises(ValueError):
        FlowSample(
            t_s=0, net_direction="in", magnitude=1.5, compaction=0.5,
        )


def test_pressure_reading_rejects_out_of_range():
    with pytest.raises(ValueError):
        PressureReading(t_s=0.0, pressure_rms=1.5)


def test_medical_candidate_rejects_empty_id():
    with pytest.raises(ValueError):
        MedicalCandidate(candidate_id="", t_s=0.0, confidence=0.9)


def test_medical_candidate_rejects_out_of_unit_confidence():
    with pytest.raises(ValueError):
        MedicalCandidate(
            candidate_id="c", t_s=0.0, confidence=1.2,
        )


# ---------------------------------------------------------------------------
# ZoneObservation
# ---------------------------------------------------------------------------


def test_zone_observation_rejects_empty_id():
    with pytest.raises(ValueError):
        ZoneObservation(
            zone_id="", zone_kind="standing",
            window_duration_s=10.0,
        )


def test_zone_observation_rejects_unknown_kind():
    with pytest.raises(ValueError):
        ZoneObservation(
            zone_id="z", zone_kind="balcony",  # type: ignore[arg-type]
            window_duration_s=10.0,
        )


def test_zone_observation_rejects_non_positive_duration():
    with pytest.raises(ValueError):
        ZoneObservation(
            zone_id="z", zone_kind="seating",
            window_duration_s=0,
        )


# ---------------------------------------------------------------------------
# CrowdScore
# ---------------------------------------------------------------------------


def test_crowd_score_rejects_out_of_unit():
    with pytest.raises(ValueError):
        CrowdScore(
            zone_id="z",
            density_safety=1.5, flow_safety=1.0,
            pressure_safety=1.0, medical_safety=1.0,
            overall=1.0, alert_level="ok",
        )


def test_crowd_score_rejects_unknown_level():
    with pytest.raises(ValueError):
        CrowdScore(
            zone_id="z",
            density_safety=1.0, flow_safety=1.0,
            pressure_safety=1.0, medical_safety=1.0,
            overall=1.0, alert_level="critical",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# VenueOpsAlert — 6-boundary claims guard
# ---------------------------------------------------------------------------


def test_alert_allows_physics_text():
    alert = VenueOpsAlert(
        zone_id="Z",
        kind="density",
        level="watch",
        text="Zone density rising: 5.2 p/m² over the last 3 min. Venue-ops: consider metering entry.",
    )
    assert alert.level == "watch"


@pytest.mark.parametrize(
    "bad_text",
    [
        "Diagnose seizure in zone C.",
        "Seizure in zone C.",
        "Heart attack reported.",
        "Stroke signature detected.",
        "Overdose suspected.",
        "Pronounced deceased.",
    ],
)
def test_alert_rejects_clinical_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        VenueOpsAlert(zone_id="Z", kind="medical", level="urgent", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Close gate B immediately.",
        "Stop entry now.",
        "Evacuate zone C.",
        "Activate the PA system.",
        "Announce over PA.",
        "Disperse the crowd.",
        "Remove the attendee.",
        "Call 911 now.",
        "Dispatch ambulance.",
    ],
)
def test_alert_rejects_operational_command_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        VenueOpsAlert(zone_id="Z", kind="density", level="urgent", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Person in red shirt collapsed.",
        "Person wearing a hat.",
        "Same attendee as earlier.",
        "Identify the attendee.",
        "Biometric match found.",
        "Facial print matched.",
        "Use face recognition to track.",
    ],
)
def test_alert_rejects_privacy_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        VenueOpsAlert(zone_id="Z", kind="medical", level="watch", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Drunk attendee in zone C.",
        "Intoxicated attendee fallen.",
        "Rowdy attendee pushing.",
        "Belligerent attendee.",
    ],
)
def test_alert_rejects_dignity_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        VenueOpsAlert(zone_id="Z", kind="medical", level="watch", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Security-guard performance dropped.",
        "Guard performance metric missed.",
        "Discipline the guard for missed alert.",
        "Guard write-up recommended.",
        "Guard reprimand warranted.",
    ],
)
def test_alert_rejects_labor_relations_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        VenueOpsAlert(zone_id="Z", kind="density", level="watch", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Stampede imminent in zone C.",
        "Crush in progress.",
        "Crush forming at choke point.",
        "Disaster unfolding.",
        "Catastrophe at zone C.",
        "Catastrophic density readings.",
        "Fatality detected.",
        "Fatalities likely.",
        "Panic detected in crowd.",
        "Mass casualty event forming.",
        "Mass-casualty conditions.",
        "Immediate danger in zone C.",
        "Imminent danger.",
        "Lethal density readings.",
        "Deadly compaction.",
    ],
)
def test_alert_rejects_panic_inducing_vocabulary(bad_text: str):
    """The NEW boundary in this sibling. Dramatic vocabulary
    that, when relayed through venue radios / PA, creates the
    very event it warns about."""
    with pytest.raises(ValueError):
        VenueOpsAlert(zone_id="Z", kind="density", level="urgent", text=bad_text)


def test_alert_rejects_empty_text():
    with pytest.raises(ValueError):
        VenueOpsAlert(zone_id="Z", kind="density", level="ok", text="  ")


def test_alert_rejects_unknown_kind():
    with pytest.raises(ValueError):
        VenueOpsAlert(
            zone_id="Z", kind="weather",  # type: ignore[arg-type]
            level="watch", text="rain",
        )


# ---------------------------------------------------------------------------
# VenueReport
# ---------------------------------------------------------------------------


def test_venue_report_rejects_empty_id():
    with pytest.raises(ValueError):
        VenueReport(venue_id="")


def test_venue_report_filters_by_level_and_kind():
    alert_a = VenueOpsAlert(
        zone_id="Z1", kind="density", level="watch",
        text="Zone density elevated. Venue-ops: keep in view.",
    )
    alert_b = VenueOpsAlert(
        zone_id="Z2", kind="pressure", level="urgent",
        text="Zone pressure elevated. Venue-ops: consider metering entry upstream.",
    )
    report = VenueReport(venue_id="V", alerts=[alert_a, alert_b])
    assert len(report.alerts_at_level("urgent")) == 1
    assert report.alerts_at_level("urgent")[0].kind == "pressure"
    assert len(report.alerts_of_kind("density")) == 1


def test_venue_report_as_text_without_alerts():
    report = VenueReport(venue_id="V")
    text = report.as_text()
    assert "V" in text
    assert "No watch" in text

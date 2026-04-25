"""Tests for core dataclasses + multi-list claims guard."""

from __future__ import annotations

import pytest

from triage4_fish.core.models import (
    FarmManagerAlert,
    GillRateSample,
    MortalityFloorSample,
    PenObservation,
    PenReport,
    PenWelfareScore,
    SchoolCohesionSample,
    SeaLiceSample,
    WaterChemistrySample,
)


# ---------------------------------------------------------------------------
# Sample types
# ---------------------------------------------------------------------------


def test_gill_rate_rejects_implausible():
    with pytest.raises(ValueError):
        GillRateSample(t_s=0.0, rate_bpm=500.0)


def test_school_cohesion_rejects_out_of_unit():
    with pytest.raises(ValueError):
        SchoolCohesionSample(t_s=0.0, cohesion=1.5)


def test_sea_lice_rejects_out_of_unit_count_proxy():
    with pytest.raises(ValueError):
        SeaLiceSample(
            t_s=0.0, count_proxy=1.5, classifier_confidence=0.8,
        )


def test_sea_lice_rejects_out_of_unit_confidence():
    with pytest.raises(ValueError):
        SeaLiceSample(
            t_s=0.0, count_proxy=0.5, classifier_confidence=1.5,
        )


def test_mortality_rejects_implausible_count():
    with pytest.raises(ValueError):
        MortalityFloorSample(t_s=0.0, count=100000, confidence=0.8)


def test_water_chemistry_rejects_implausible_do():
    with pytest.raises(ValueError):
        WaterChemistrySample(
            t_s=0.0, dissolved_oxygen_mg_l=50.0,
            temperature_c=12.0, salinity_ppt=32.0,
            turbidity_ntu=2.0,
        )


def test_water_chemistry_rejects_implausible_temp():
    with pytest.raises(ValueError):
        WaterChemistrySample(
            t_s=0.0, dissolved_oxygen_mg_l=8.0,
            temperature_c=100.0, salinity_ppt=32.0,
            turbidity_ntu=2.0,
        )


# ---------------------------------------------------------------------------
# PenObservation
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_pen_id():
    with pytest.raises(ValueError):
        PenObservation(
            pen_id="", species="salmon",
            location_handle="pen-A", window_duration_s=600.0,
        )


def test_observation_rejects_unknown_species():
    with pytest.raises(ValueError):
        PenObservation(
            pen_id="P", species="koi",  # type: ignore[arg-type]
            location_handle="pen-A", window_duration_s=600.0,
        )


def test_observation_rejects_decimal_coords_in_handle():
    """Field-security boundary inherited from triage4-wild —
    offshore tuna / bluefin pens are theft targets."""
    with pytest.raises(ValueError, match="decimal-degree"):
        PenObservation(
            pen_id="P", species="salmon",
            location_handle="60.123, -5.678",
            window_duration_s=600.0,
        )


def test_observation_rejects_bad_water_condition():
    with pytest.raises(ValueError):
        PenObservation(
            pen_id="P", species="salmon",
            location_handle="pen-A", window_duration_s=600.0,
            water_condition="freezing",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# PenWelfareScore
# ---------------------------------------------------------------------------


def test_score_rejects_out_of_unit():
    with pytest.raises(ValueError):
        PenWelfareScore(
            pen_id="P",
            gill_rate_safety=1.5, school_cohesion_safety=1.0,
            sea_lice_safety=1.0, mortality_safety=1.0,
            water_chemistry_safety=1.0, overall=1.0,
            welfare_level="steady",
        )


# ---------------------------------------------------------------------------
# FarmManagerAlert — multi-list claims guard
# ---------------------------------------------------------------------------


def _valid_alert_kwargs() -> dict:
    return dict(
        pen_id="P", kind="gill_rate", level="urgent",
        text="URGENT (salmon, P, pen-A1): gill-rate aggregate outside species reference band. Vet review recommended.",
        location_handle="pen-A1",
    )


def test_alert_valid_construction():
    a = FarmManagerAlert(**_valid_alert_kwargs())
    assert a.kind == "gill_rate"


# ---------------------------------------------------------------------------
# Antibiotic-dosing-overreach boundary — NEW in this sibling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Administer antibiotic at 50 mg/kg.",
        "Administer antimicrobial today.",
        "Dose with oxytetracycline.",
        "Dosing recommendation: 60 mg/kg.",
        "Prescribe antimicrobial course.",
        "Prescribe antibiotic regimen.",
        "Treatment regimen attached.",
        "Course of treatment 10 days.",
        "Withdrawal period 14 days.",
        "Start oxytetracycline today.",
        "Florfenicol indicated.",
        "Emamectin treatment recommended.",
        "Azamethiphos bath needed.",
        "Switch to medicated feed.",
    ],
)
def test_alert_rejects_antibiotic_dosing_overreach(bad_text: str):
    """Aquaculture-specific NEW boundary. Dosing decisions
    are veterinary practice."""
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError, match="antibiotic-dosing-overreach"):
        FarmManagerAlert(**kwargs)


# ---------------------------------------------------------------------------
# Veterinary-practice boundary — inherited from triage4-farm
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Diagnose disease pattern.",
        "Diagnosis suggests parasitic.",
        "Prescribe action.",
        "Medicate the pen.",
        "Medication regimen attached.",
        "Therapy plan included.",
    ],
)
def test_alert_rejects_veterinary_practice(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        FarmManagerAlert(**kwargs)


# ---------------------------------------------------------------------------
# Outbreak-diagnosis-overreach — inherited from triage4-bird
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Outbreak detected pen-A1.",
        "Outbreak confirmed.",
        "Epidemic underway.",
        "Pandemic conditions.",
        "Disease confirmed.",
        "ISA confirmed pen-A1.",
        "ISAv confirmed via vision.",
        "PD confirmed today.",
        "IPN confirmed.",
        "SAV confirmed today.",
    ],
)
def test_alert_rejects_outbreak_overreach(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        FarmManagerAlert(**kwargs)


# ---------------------------------------------------------------------------
# No-false-reassurance — strongest in catalog
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Pen is healthy this pass.",
        "No outbreak this window.",
        "Stock is safe.",
        "Stocks are safe across the farm.",
        "Clean bill of health.",
        "No concerns this window.",
        "No welfare concerns.",
        "All pens safe this morning.",
        "No disease patterns observed.",
        "Disease-free pass.",
    ],
)
def test_alert_rejects_no_false_reassurance(bad_text: str):
    """Strongest no-false-reassurance posture in the
    catalog — failure-cost asymmetry rationale."""
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError, match="no-false-reassurance"):
        FarmManagerAlert(**kwargs)


# ---------------------------------------------------------------------------
# Field-security — inherited
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Latitude 60.5 longitude -5.5 pen-A1.",
        "GPS coordinates: 60.5, -5.5.",
        "Coordinates: pen-A1 60.5.",
        "lat: 60.5 pen-A1.",
        "Located at offshore site.",
    ],
)
def test_alert_rejects_field_security(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        FarmManagerAlert(**kwargs)


def test_alert_rejects_decimal_coords_in_text():
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = "URGENT pen at 60.123, -5.678 today."
    with pytest.raises(ValueError):
        FarmManagerAlert(**kwargs)


def test_alert_rejects_decimal_coords_in_handle():
    kwargs = _valid_alert_kwargs()
    kwargs["location_handle"] = "60.123, -5.678"
    with pytest.raises(ValueError):
        FarmManagerAlert(**kwargs)


# ---------------------------------------------------------------------------
# Operational + panic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Cull the pen tomorrow.",
        "Harvest now indicated.",
        "Move stock to neighbouring pen.",
        "Dump the pen.",
    ],
)
def test_alert_rejects_operational(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        FarmManagerAlert(**kwargs)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Disaster unfolding pen-A1.",
        "Catastrophe at pen-A2.",
        "Mass mortality event.",
    ],
)
def test_alert_rejects_panic(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        FarmManagerAlert(**kwargs)


def test_alert_rejects_empty_text():
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = "  "
    with pytest.raises(ValueError):
        FarmManagerAlert(**kwargs)


# ---------------------------------------------------------------------------
# PenReport — strongest no-false-reassurance text
# ---------------------------------------------------------------------------


def test_report_rejects_empty_id():
    with pytest.raises(ValueError):
        PenReport(farm_id="")


def test_report_as_text_no_alerts_explicit_no_clearance():
    """Critical property — empty alert list produces the
    strongest no-false-reassurance text in the catalog."""
    report = PenReport(farm_id="F1")
    text = report.as_text().lower()
    assert "is not a clearance" in text
    assert "review remains required" in text
    # Critically, none of the reassurance phrases that would
    # be rejected if emitted through a FarmManagerAlert.
    for phrase in (
        "all pens safe", "no outbreak", "clean bill of health",
        "no concerns", "disease-free",
    ):
        assert phrase not in text


def test_report_filters_by_level_and_kind():
    a_watch = FarmManagerAlert(
        pen_id="P1", kind="gill_rate", level="watch",
        text="WATCH (salmon, P1, pen-A1): gill-rate aggregate trending outside band.",
        location_handle="pen-A1",
    )
    a_urgent = FarmManagerAlert(
        pen_id="P2", kind="mortality_floor", level="urgent",
        text="URGENT (salmon, P2, pen-B1): candidate mortality cluster. Vet review recommended.",
        location_handle="pen-B1",
    )
    report = PenReport(farm_id="F", alerts=[a_watch, a_urgent])
    assert len(report.alerts_at_level("urgent")) == 1
    assert report.alerts_at_level("urgent")[0].kind == "mortality_floor"
    assert len(report.alerts_of_kind("gill_rate")) == 1

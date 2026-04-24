"""Tests for core dataclasses — field-security + SMS cap + guards."""

from __future__ import annotations

import pytest

from triage4_wild.core.enums import MAX_RANGER_SMS_CHARS
from triage4_wild.core.models import (
    BodyConditionSample,
    GaitSample,
    LocationHandle,
    QuadrupedPoseSample,
    RangerAlert,
    ReserveReport,
    ThermalSample,
    ThreatConfidence,
    WildlifeHealthScore,
    WildlifeObservation,
)


# ---------------------------------------------------------------------------
# LocationHandle — field-security boundary
# ---------------------------------------------------------------------------


def test_location_handle_accepts_grid_token():
    h = LocationHandle(handle="grid-A7")
    assert h.handle == "grid-A7"


def test_location_handle_accepts_zone_token():
    h = LocationHandle(handle="zone-central")
    assert h.handle == "zone-central"


def test_location_handle_rejects_empty():
    with pytest.raises(ValueError):
        LocationHandle(handle="")


@pytest.mark.parametrize(
    "bad_handle",
    [
        "1.2345, -36.7890",
        "1.234 -36.789",
        "-1.234, 5.678",
        "grid-A7 1.234, 5.678",  # token + leaked coords
    ],
)
def test_location_handle_rejects_decimal_patterns(bad_handle: str):
    """Field-security boundary — plaintext decimal-degree
    coordinates NEVER enter the library."""
    with pytest.raises(ValueError, match="decimal-"):
        LocationHandle(handle=bad_handle)


def test_location_handle_single_decimal_doesnt_trigger():
    """A single integer or single-decimal number is not a
    coordinate pair and shouldn't trigger the guard."""
    # grid-3.4 alone is not a coordinate pair.
    h = LocationHandle(handle="subgrid-3.4a")
    assert h.handle == "subgrid-3.4a"


# ---------------------------------------------------------------------------
# Raw samples
# ---------------------------------------------------------------------------


def test_pose_sample_rejects_out_of_unit():
    with pytest.raises(ValueError):
        QuadrupedPoseSample(
            t_s=0.0, limb_asymmetry=1.5, body_upright=0.5,
        )


def test_thermal_sample_rejects_out_of_unit():
    with pytest.raises(ValueError):
        ThermalSample(t_s=0.0, hotspot=1.5)


def test_gait_sample_rejects_implausible_pace():
    with pytest.raises(ValueError):
        GaitSample(t_s=0.0, pace_mps=50.0, cadence_steadiness=0.9)


def test_body_condition_sample_rejects_out_of_unit():
    with pytest.raises(ValueError):
        BodyConditionSample(t_s=0.0, condition_score=1.5)


def test_threat_confidence_rejects_unknown_kind():
    with pytest.raises(ValueError):
        ThreatConfidence(
            kind="horn_cracks",  # type: ignore[arg-type]
            confidence=0.5,
        )


# ---------------------------------------------------------------------------
# WildlifeObservation
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_token():
    with pytest.raises(ValueError):
        WildlifeObservation(
            obs_token="", species="elephant",
            species_confidence=0.9, window_duration_s=30.0,
            location=LocationHandle(handle="grid-A"),
        )


def test_observation_rejects_unknown_species():
    with pytest.raises(ValueError):
        WildlifeObservation(
            obs_token="O", species="koala",  # type: ignore[arg-type]
            species_confidence=0.9, window_duration_s=30.0,
            location=LocationHandle(handle="grid-A"),
        )


def test_observation_rejects_bad_duration():
    with pytest.raises(ValueError):
        WildlifeObservation(
            obs_token="O", species="elephant",
            species_confidence=0.9, window_duration_s=0,
            location=LocationHandle(handle="grid-A"),
        )


def test_observation_rejects_bad_capture_quality():
    with pytest.raises(ValueError):
        WildlifeObservation(
            obs_token="O", species="elephant",
            species_confidence=0.9, window_duration_s=30.0,
            location=LocationHandle(handle="grid-A"),
            capture_quality="foggy",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# WildlifeHealthScore
# ---------------------------------------------------------------------------


def test_score_rejects_out_of_unit():
    with pytest.raises(ValueError):
        WildlifeHealthScore(
            obs_token="O",
            gait_safety=1.5, thermal_safety=1.0,
            postural_safety=1.0, body_condition_safety=1.0,
            threat_signal=1.0, overall=1.0, alert_level="ok",
        )


# ---------------------------------------------------------------------------
# RangerAlert — field-security + SMS-cap + new boundaries
# ---------------------------------------------------------------------------


def _valid_alert_kwargs() -> dict:
    return dict(
        obs_token="O",
        kind="gait",
        level="urgent",
        text="URGENT (elephant, grid-A7): gait asymmetry. Ranger + reserve vet review.",
        location_handle="grid-A7",
    )


def test_alert_valid_construction():
    a = RangerAlert(**_valid_alert_kwargs())
    assert a.kind == "gait"
    assert len(a.text) <= MAX_RANGER_SMS_CHARS


def test_alert_rejects_empty_text():
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = "   "
    with pytest.raises(ValueError):
        RangerAlert(**kwargs)


# ---------------------------------------------------------------------------
# Field-security boundary — new in this sibling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Elephant at latitude 1.234 grid-A7.",
        "Longitude 36.789 observed.",
        "lat: 1.234 elephant grid-A7.",
        "lng: 36.789 zebra.",
        "lon: -36.789 rhino.",
        "GPS coordinates: grid-A7 elephant.",
        "Coordinates: grid-A7 elephant.",
        "Located at grid-A7 elephant injured.",
    ],
)
def test_alert_rejects_field_security_vocabulary(bad_text: str):
    """Field-security boundary — the library never leaks
    location vocabulary into ranger output."""
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        RangerAlert(**kwargs)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Elephant at 1.234, 36.789 sighted.",
        "URGENT (elephant, grid-A7): 1.234 -36.789 observed.",
        "Zebra at -1.234, 5.678 grid-A7.",
    ],
)
def test_alert_rejects_decimal_coord_patterns_in_text(bad_text: str):
    """Body text with embedded decimal coordinates also
    blocked, not just the location_handle field."""
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        RangerAlert(**kwargs)


def test_alert_rejects_decimal_coords_in_location_handle():
    kwargs = _valid_alert_kwargs()
    kwargs["location_handle"] = "1.234, 36.789"
    with pytest.raises(ValueError):
        RangerAlert(**kwargs)


# ---------------------------------------------------------------------------
# Poaching-prediction overreach boundary — new in this sibling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Predict poacher activity at grid-A7.",
        "Predict poaching event tomorrow.",
        "Likely poacher trail visible.",
        "Suspect poacher near grid-A7.",
        "Identify poacher from pattern.",
        "Optimise patrol route for grid-A7.",
        "Optimize patrol route for grid-A7.",
        "Schedule patrol route overnight.",
        "Patrol route recommendation attached.",
        "Anti-poaching operation recommended.",
    ],
)
def test_alert_rejects_poaching_overreach(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError, match="poaching"):
        RangerAlert(**kwargs)


# ---------------------------------------------------------------------------
# Ecosystem-prediction overreach boundary — new in this sibling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Population trajectory shows decline.",
        "Predict extinction within ten years.",
        "Extinction risk is elevated.",
        "Species will disappear within decade.",
        "Conservation outcome is negative.",
        "Conservation outcome prediction attached.",
    ],
)
def test_alert_rejects_ecosystem_overreach(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError, match="ecosystem"):
        RangerAlert(**kwargs)


# ---------------------------------------------------------------------------
# Standard boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Elephant is injured at grid-A7.",
        "Zebra has a wound observed.",
        "Confirms snare presence grid-A7.",
        "Diagnosis: gastrointestinal parasites.",
        "Rhino is in shock pattern grid-A7.",
        "Giraffe is suffering grid-A7.",
    ],
)
def test_alert_rejects_clinical_vocabulary(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        RangerAlert(**kwargs)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Intercept poacher near grid-A7.",
        "Deploy patrol to grid-A7 zone.",
        "Dispatch rangers to grid-A7 now.",
        "Apprehend suspect near grid-A7.",
        "Detain intruder at grid-A7.",
    ],
)
def test_alert_rejects_operational_vocabulary(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        RangerAlert(**kwargs)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Herd is safe this pass grid-A7.",
        "No threats detected this cycle.",
        "All clear at grid-A7 pass.",
    ],
)
def test_alert_rejects_reassurance(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        RangerAlert(**kwargs)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Tragedy observed at grid-A7.",
        "Catastrophe in zone-central.",
        "Fatalities at grid-A7.",
    ],
)
def test_alert_rejects_panic_vocabulary(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        RangerAlert(**kwargs)


# ---------------------------------------------------------------------------
# SMS-length structural cap — new in this sibling
# ---------------------------------------------------------------------------


def test_alert_rejects_text_longer_than_sms_cap():
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = "X" * (MAX_RANGER_SMS_CHARS + 1)
    with pytest.raises(ValueError, match="SMS"):
        RangerAlert(**kwargs)


def test_alert_accepts_text_at_sms_cap():
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = "A" * MAX_RANGER_SMS_CHARS
    a = RangerAlert(**kwargs)
    assert len(a.text) == MAX_RANGER_SMS_CHARS


def test_alert_rejects_unknown_kind():
    kwargs = _valid_alert_kwargs()
    kwargs["kind"] = "weather"
    with pytest.raises(ValueError):
        RangerAlert(**kwargs)


# ---------------------------------------------------------------------------
# ReserveReport
# ---------------------------------------------------------------------------


def test_report_rejects_empty_id():
    with pytest.raises(ValueError):
        ReserveReport(reserve_id="")


def test_report_as_text_no_alerts_is_not_reassuring():
    """Empty alert list must NOT produce 'all clear' text."""
    report = ReserveReport(reserve_id="R1")
    text = report.as_text().lower()
    assert "ranger attention remains required" in text
    # None of the reassurance phrases that would be rejected
    # if emitted through a RangerAlert.
    for phrase in (
        "all clear",
        "herd is safe",
        "no threats detected",
    ):
        assert phrase not in text


def test_report_filters_by_level_and_kind():
    a_watch = RangerAlert(
        obs_token="O1", kind="gait", level="watch",
        text="WATCH (zebra, grid-A): gait asymmetry. Ranger review next pass.",
        location_handle="grid-A",
    )
    a_urgent = RangerAlert(
        obs_token="O2", kind="thermal", level="urgent",
        text="URGENT (buffalo, grid-B): focal thermal hotspot. Ranger + reserve vet review.",
        location_handle="grid-B",
    )
    report = ReserveReport(reserve_id="R", alerts=[a_watch, a_urgent])
    assert len(report.alerts_at_level("urgent")) == 1
    assert report.alerts_at_level("urgent")[0].kind == "thermal"
    assert len(report.alerts_of_kind("gait")) == 1

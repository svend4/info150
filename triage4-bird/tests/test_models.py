"""Tests for core dataclasses + new boundaries."""

from __future__ import annotations

import pytest

from triage4_bird.core.enums import MAX_AVIAN_SMS_CHARS
from triage4_bird.core.models import (
    AvianHealthScore,
    BirdObservation,
    BodyThermalSample,
    CallSample,
    DeadBirdCandidate,
    OrnithologistAlert,
    StationReport,
    WingbeatSample,
)


# ---------------------------------------------------------------------------
# Sample types
# ---------------------------------------------------------------------------


def test_call_sample_has_no_audio_field():
    """Architectural property: the dataclass shape REFUSES
    raw audio. Confirm by reflection that no audio-payload
    field exists."""
    forbidden_field_names = {
        "audio", "waveform", "samples_pcm", "wav_bytes", "raw_audio",
    }
    fields = set(CallSample.__dataclass_fields__.keys())
    assert not (fields & forbidden_field_names)


def test_call_sample_rejects_unknown_kind():
    with pytest.raises(ValueError):
        CallSample(
            t_s=0.0, species="robin",
            kind="quack",  # type: ignore[arg-type]
            confidence=0.8,
        )


def test_call_sample_rejects_unknown_species():
    with pytest.raises(ValueError):
        CallSample(
            t_s=0.0, species="penguin",  # type: ignore[arg-type]
            kind="song", confidence=0.8,
        )


def test_call_sample_rejects_out_of_unit_confidence():
    with pytest.raises(ValueError):
        CallSample(t_s=0.0, species="robin", kind="song", confidence=1.5)


def test_wingbeat_sample_rejects_implausible_frequency():
    with pytest.raises(ValueError):
        WingbeatSample(t_s=0.0, frequency_hz=200.0, reliable=True)


def test_thermal_sample_rejects_out_of_unit():
    with pytest.raises(ValueError):
        BodyThermalSample(t_s=0.0, elevation=1.5)


def test_dead_bird_candidate_rejects_out_of_unit_confidence():
    with pytest.raises(ValueError):
        DeadBirdCandidate(t_s=0.0, confidence=1.5)


# ---------------------------------------------------------------------------
# BirdObservation
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_token():
    with pytest.raises(ValueError):
        BirdObservation(
            obs_token="", station_id="A",
            location_handle="grid-1", window_duration_s=60.0,
        )


def test_observation_rejects_empty_station_id():
    with pytest.raises(ValueError):
        BirdObservation(
            obs_token="O", station_id="",
            location_handle="grid-1", window_duration_s=60.0,
        )


def test_observation_rejects_decimal_coords_in_handle():
    """Field-security boundary inherited from triage4-wild."""
    with pytest.raises(ValueError, match="decimal-degree"):
        BirdObservation(
            obs_token="O", station_id="A",
            location_handle="1.234, 36.789",
            window_duration_s=60.0,
        )


def test_observation_rejects_bad_duration():
    with pytest.raises(ValueError):
        BirdObservation(
            obs_token="O", station_id="A",
            location_handle="grid-1", window_duration_s=0,
        )


def test_observation_rejects_unknown_expected_species():
    with pytest.raises(ValueError):
        BirdObservation(
            obs_token="O", station_id="A",
            location_handle="grid-1", window_duration_s=60.0,
            expected_species=("penguin",),  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# AvianHealthScore
# ---------------------------------------------------------------------------


def test_score_rejects_out_of_unit():
    with pytest.raises(ValueError):
        AvianHealthScore(
            obs_token="O",
            call_presence_safety=1.5, distress_safety=1.0,
            vitals_safety=1.0, thermal_safety=1.0,
            mortality_cluster_safety=1.0, overall=1.0,
            alert_level="ok",
        )


# ---------------------------------------------------------------------------
# OrnithologistAlert — multi-list claims guard
# ---------------------------------------------------------------------------


def _valid_alert_kwargs() -> dict:
    return dict(
        obs_token="O", kind="distress", level="urgent",
        text="URGENT (station-A, grid-1): distress vocalisations frequent across this window. Ornithologist + reserve-vet review.",
        location_handle="grid-1",
    )


def test_alert_valid_construction():
    a = OrnithologistAlert(**_valid_alert_kwargs())
    assert a.kind == "distress"
    assert len(a.text) <= MAX_AVIAN_SMS_CHARS


# ---------------------------------------------------------------------------
# Surveillance-overreach boundary — NEW in this sibling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Detects avian flu at station-A.",
        "Detects HPAI in mallards.",
        "Diagnoses avian flu strain.",
        "Diagnoses HPAI in window.",
        "Confirms outbreak at station-A.",
        "Predicts outbreak by next week.",
        "Flu strain identified in window.",
        "Epidemic detected this morning.",
        "Pandemic conditions unfolding.",
        "H5N1 confirmed at station-A.",
        "H7N9 candidate cluster.",
        "H5N8 detected this window.",
    ],
)
def test_alert_rejects_surveillance_overreach(bad_text: str):
    """The library never claims to diagnose / detect avian
    flu / HPAI — that's a public-health call from a sampling
    lab."""
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError, match="surveillance"):
        OrnithologistAlert(**kwargs)


# ---------------------------------------------------------------------------
# Audio-privacy boundary — NEW in this sibling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Person said hello at station-A.",
        "Someone said the word.",
        "Voice content captured.",
        "Conversation captured between visitors.",
        "Human speech in window.",
        "Audio of speaker recorded.",
        "Quoted speech follows.",
        "Transcribed audio attached.",
    ],
)
def test_alert_rejects_audio_privacy_vocabulary(bad_text: str):
    """The library never echoes recorded human speech."""
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError, match="audio-privacy"):
        OrnithologistAlert(**kwargs)


# ---------------------------------------------------------------------------
# Field-security boundary — inherited from triage4-wild
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Bird at latitude 1.234 grid-1.",
        "Longitude 36.789 station-A.",
        "lat: 1.234 station-A.",
        "lng: 36.789 station-A.",
        "lon: -36.789 station-A.",
        "GPS coordinates: grid-1.",
        "Coordinates: grid-1 station-A.",
        "Located at grid-1 station-A.",
    ],
)
def test_alert_rejects_field_security_vocabulary(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        OrnithologistAlert(**kwargs)


def test_alert_rejects_decimal_coords_in_text():
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = "URGENT: bird at 1.234, 36.789 grid-1."
    with pytest.raises(ValueError):
        OrnithologistAlert(**kwargs)


def test_alert_rejects_decimal_coords_in_location_handle():
    kwargs = _valid_alert_kwargs()
    kwargs["location_handle"] = "1.234, 36.789"
    with pytest.raises(ValueError):
        OrnithologistAlert(**kwargs)


# ---------------------------------------------------------------------------
# Standard inherited boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_text",
    [
        "Bird is sick at station-A.",
        "Has rabies pattern at grid-1.",
        "Has HPAI signature in window.",
        "Bird is infected.",
        "Confirms presence of pathogen.",
        "Diagnosis: respiratory.",
    ],
)
def test_alert_rejects_clinical_vocabulary(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        OrnithologistAlert(**kwargs)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Cull birds at station-A.",
        "Destroy nest at grid-1.",
        "Remove carcass from grid-1.",
        "Dispatch sampler to station-A.",
        "Deploy sampling team now.",
    ],
)
def test_alert_rejects_operational_vocabulary(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        OrnithologistAlert(**kwargs)


@pytest.mark.parametrize(
    "bad_text",
    [
        "No flu at station-A.",
        "All clear this window.",
        "No concerns observed.",
    ],
)
def test_alert_rejects_reassurance(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        OrnithologistAlert(**kwargs)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Tragedy at station-A.",
        "Catastrophe in zone-north.",
        "Disaster at grid-1.",
    ],
)
def test_alert_rejects_panic_vocabulary(bad_text: str):
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = bad_text
    with pytest.raises(ValueError):
        OrnithologistAlert(**kwargs)


# ---------------------------------------------------------------------------
# SMS-cap inherited
# ---------------------------------------------------------------------------


def test_alert_rejects_text_longer_than_sms_cap():
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = "A" * (MAX_AVIAN_SMS_CHARS + 1)
    with pytest.raises(ValueError, match="SMS"):
        OrnithologistAlert(**kwargs)


def test_alert_accepts_text_at_sms_cap():
    kwargs = _valid_alert_kwargs()
    kwargs["text"] = "A" * MAX_AVIAN_SMS_CHARS
    a = OrnithologistAlert(**kwargs)
    assert len(a.text) == MAX_AVIAN_SMS_CHARS


# ---------------------------------------------------------------------------
# StationReport
# ---------------------------------------------------------------------------


def test_report_rejects_empty_id():
    with pytest.raises(ValueError):
        StationReport(station_id="")


def test_report_as_text_no_alerts_is_observation_worded():
    """Empty alert list → observation-worded text, never
    reassurance."""
    report = StationReport(station_id="A")
    text = report.as_text().lower()
    assert "ornithologist" in text
    assert "remains required" in text
    for phrase in ("all clear", "no flu", "no concerns"):
        assert phrase not in text


def test_report_filters_by_level_and_kind():
    a_watch = OrnithologistAlert(
        obs_token="O", kind="distress", level="watch",
        text="WATCH (station-A, grid-1): distress vocalisations elevated this window. Ornithologist + reserve-vet review.",
        location_handle="grid-1",
    )
    a_urgent = OrnithologistAlert(
        obs_token="O", kind="mortality_cluster", level="urgent",
        text="URGENT (station-A, grid-1): candidate mortality cluster — sampling recommended.",
        location_handle="grid-1",
    )
    report = StationReport(station_id="A", alerts=[a_watch, a_urgent])
    assert len(report.alerts_at_level("urgent")) == 1
    assert report.alerts_at_level("urgent")[0].kind == "mortality_cluster"
    assert len(report.alerts_of_kind("distress")) == 1

"""Tests for the core dataclasses + 7-boundary claims guard."""

from __future__ import annotations

import pytest

from triage4_aqua.core.models import (
    AquaticScore,
    LifeguardAlert,
    PoolReport,
    SubmersionSample,
    SurfacePoseSample,
    SwimmerObservation,
    SwimmerPresenceSample,
)


# ---------------------------------------------------------------------------
# Sample types
# ---------------------------------------------------------------------------


def test_surface_sample_rejects_out_of_unit():
    with pytest.raises(ValueError):
        SurfacePoseSample(
            t_s=0, head_height_rel=1.5,
            body_vertical=0.5, motion_rhythm=0.5,
        )


def test_surface_sample_rejects_negative_time():
    with pytest.raises(ValueError):
        SurfacePoseSample(
            t_s=-1, head_height_rel=0.5,
            body_vertical=0.5, motion_rhythm=0.5,
        )


def test_submersion_sample_accepts_boolean():
    s = SubmersionSample(t_s=1.0, submerged=True)
    assert s.submerged is True


def test_submersion_sample_rejects_negative_time():
    with pytest.raises(ValueError):
        SubmersionSample(t_s=-0.5, submerged=False)


def test_presence_sample_rejects_negative_time():
    with pytest.raises(ValueError):
        SwimmerPresenceSample(t_s=-0.1, active=True)


# ---------------------------------------------------------------------------
# SwimmerObservation
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_token():
    with pytest.raises(ValueError):
        SwimmerObservation(
            swimmer_token="", zone="pool", window_duration_s=30.0,
        )


def test_observation_rejects_unknown_zone():
    with pytest.raises(ValueError):
        SwimmerObservation(
            swimmer_token="s", zone="ocean",  # type: ignore[arg-type]
            window_duration_s=30.0,
        )


def test_observation_rejects_bad_condition():
    with pytest.raises(ValueError):
        SwimmerObservation(
            swimmer_token="s", zone="pool",
            window_duration_s=30.0,
            pool_condition="rainy",  # type: ignore[arg-type]
        )


def test_observation_rejects_non_positive_duration():
    with pytest.raises(ValueError):
        SwimmerObservation(
            swimmer_token="s", zone="pool", window_duration_s=0,
        )


# ---------------------------------------------------------------------------
# AquaticScore
# ---------------------------------------------------------------------------


def test_score_rejects_out_of_unit():
    with pytest.raises(ValueError):
        AquaticScore(
            swimmer_token="s",
            submersion_safety=1.5, idr_safety=1.0,
            absent_safety=1.0, distress_safety=1.0,
            overall=1.0, alert_level="ok",
        )


def test_score_rejects_unknown_level():
    with pytest.raises(ValueError):
        AquaticScore(
            swimmer_token="s",
            submersion_safety=1.0, idr_safety=1.0,
            absent_safety=1.0, distress_safety=1.0,
            overall=1.0, alert_level="critical",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# LifeguardAlert — 7-boundary claims guard
# ---------------------------------------------------------------------------


def test_alert_allows_observational_text():
    alert = LifeguardAlert(
        swimmer_token="S",
        kind="submersion",
        level="urgent",
        text="Swimmer S zone pool: sustained submersion across this cycle. Lifeguard: immediate attention warranted.",
    )
    assert alert.level == "urgent"


@pytest.mark.parametrize(
    "bad_text",
    [
        "Cardiac arrest detected.",
        "Heart attack in pool.",
        "Stroke signature.",
        "Secondary drowning risk.",
        "Dry drowning possible.",
        "Hypoxia confirmed.",
        "Hypoxic symptoms.",
        "Diagnose drowning.",
        "Pronounced deceased.",
    ],
)
def test_alert_rejects_clinical_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s", kind="submersion", level="urgent", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Call 911 immediately.",
        "Dispatch ambulance.",
        "Call emergency services.",
        "Perform CPR on the swimmer.",
        "Begin chest compressions.",
        "Defibrillate if needed.",
    ],
)
def test_alert_rejects_operational_command_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s", kind="submersion", level="urgent", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Child in red swimsuit at risk.",
        "Child wearing goggles submerged.",
        "Boy in swimsuit submerged.",
        "Girl in swimsuit missing.",
        "Female swimmer submerged.",
        "Male swimmer absent.",
        "Approximate age 8-10 submerged.",
        "Looks about 12 years old.",
        "Biometric match for swimmer.",
        "Facial print recorded.",
    ],
)
def test_alert_rejects_privacy_vocabulary(bad_text: str):
    """Child-safety-strict: the aqua-domain privacy list is the
    strictest in the monorepo."""
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s", kind="distress", level="watch", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Drowning victim in zone C.",
        "The swimmer who drowned is S-42.",
        "Overweight swimmer submerged.",
        "Unfit swimmer struggling.",
    ],
)
def test_alert_rejects_dignity_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s", kind="submersion", level="urgent", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Lifeguard performance dropped.",
        "Lifeguard performance metric missed.",
        "Lifeguard missed this signal.",
        "Lifeguard discipline recommended.",
        "Lifeguard reprimand warranted.",
        "Lifeguard write-up required.",
    ],
)
def test_alert_rejects_labor_relations_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s", kind="submersion", level="urgent", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Tragedy unfolding at pool 2.",
        "Tragic event in progress.",
        "Disaster at the beach.",
        "Catastrophe at pool 3.",
        "Catastrophic conditions.",
        "Fatality reported.",
        "Fatalities likely.",
        "Mass casualty event.",
        "Lethal conditions.",
        "Deadly pool situation.",
        "Victim count rising.",
    ],
)
def test_alert_rejects_panic_inducing_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s", kind="submersion", level="urgent", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "All clear at pool 2.",
        "Pool is safe.",
        "Beach is safe.",
        "No drowning detected.",
        "No incidents this hour.",
        "All swimmers safe.",
        "No risk observed.",
        "Confirmed safe.",
        "System confirms safety.",
        "Nothing to worry about.",
        "Rest assured.",
    ],
)
def test_alert_rejects_false_reassurance_vocabulary(bad_text: str):
    """The NEW boundary in this sibling. Language that asserts
    safety produces lifeguard complacency — the exact failure
    mode this product exists to prevent."""
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s", kind="submersion", level="ok", text=bad_text,
        )


@pytest.mark.parametrize(
    "bad_text",
    [
        "Swimmer John submerged.",
        "Swimmer Mary struggling.",
        "Swimmer Chris in distress.",
    ],
)
def test_alert_rejects_identifier_patterns(bad_text: str):
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s", kind="submersion", level="urgent", text=bad_text,
        )


def test_alert_rejects_empty_text():
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s", kind="submersion", level="ok", text="   ",
        )


def test_alert_rejects_unknown_kind():
    with pytest.raises(ValueError):
        LifeguardAlert(
            swimmer_token="s",
            kind="weather",  # type: ignore[arg-type]
            level="watch", text="rain",
        )


# ---------------------------------------------------------------------------
# PoolReport
# ---------------------------------------------------------------------------


def test_report_rejects_empty_id():
    with pytest.raises(ValueError):
        PoolReport(pool_id="")


def test_report_as_text_without_alerts_is_observation_worded():
    """Crucial: the no-false-reassurance boundary means
    PoolReport.as_text() must never say 'all clear' or
    'pool is safe'. An empty alert list should produce an
    observation-worded message instead."""
    report = PoolReport(pool_id="P1")
    text = report.as_text()
    assert "P1" in text
    # Observation-worded check.
    assert "no drowning signatures observed" in text.lower()
    # Critically — must NOT use reassurance vocabulary.
    low = text.lower()
    assert "all clear" not in low
    assert "pool is safe" not in low
    assert "all swimmers safe" not in low


def test_report_filters_by_level_and_kind():
    a = LifeguardAlert(
        swimmer_token="s1", kind="submersion", level="watch",
        text="Swimmer s1 zone pool: submersion approaching watch band.",
    )
    b = LifeguardAlert(
        swimmer_token="s2", kind="idr", level="urgent",
        text="Swimmer s2 zone pool: IDR-consistent posture. Lifeguard: immediate attention warranted.",
    )
    report = PoolReport(pool_id="P", alerts=[a, b])
    assert len(report.alerts_at_level("urgent")) == 1
    assert report.alerts_at_level("urgent")[0].kind == "idr"
    assert len(report.alerts_of_kind("submersion")) == 1

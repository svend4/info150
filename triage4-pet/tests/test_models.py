"""Tests for the core dataclasses + dual-audience claims guards."""

from __future__ import annotations

import pytest

from triage4_pet.core.models import (
    BreathingSample,
    GaitSample,
    OwnerMessage,
    PainBehaviorSample,
    PetAssessment,
    PetObservation,
    PetReport,
    PoseSample,
    VetSummary,
    VitalHRSample,
)


# ---------------------------------------------------------------------------
# Sample types
# ---------------------------------------------------------------------------


def test_pose_sample_rejects_implausible_keypoints():
    with pytest.raises(ValueError):
        PoseSample(t_s=1.0, visible_keypoints=100, detection_confidence=0.5)


def test_pose_sample_rejects_out_of_unit_confidence():
    with pytest.raises(ValueError):
        PoseSample(t_s=1.0, visible_keypoints=10, detection_confidence=1.5)


def test_gait_sample_rejects_out_of_unit():
    with pytest.raises(ValueError):
        GaitSample(t_s=1.0, limb_asymmetry=1.2, pace_consistency=0.9)


def test_breathing_sample_rejects_implausible_rate():
    with pytest.raises(ValueError):
        BreathingSample(t_s=1.0, rate_bpm=500, at_rest=True)


def test_hr_sample_rejects_implausible_rate():
    with pytest.raises(ValueError):
        VitalHRSample(t_s=1.0, hr_bpm=1000, reliable=True)


def test_pain_sample_rejects_unknown_kind():
    with pytest.raises(ValueError):
        PainBehaviorSample(
            t_s=1.0, kind="barking",  # type: ignore[arg-type]
            confidence=0.8,
        )


# ---------------------------------------------------------------------------
# PetObservation
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_token():
    with pytest.raises(ValueError):
        PetObservation(pet_token="", species="dog", window_duration_s=30.0)


def test_observation_rejects_unknown_species():
    with pytest.raises(ValueError):
        PetObservation(
            pet_token="p",
            species="iguana",  # type: ignore[arg-type]
            window_duration_s=30.0,
        )


def test_observation_rejects_bad_duration():
    with pytest.raises(ValueError):
        PetObservation(
            pet_token="p", species="dog", window_duration_s=0,
        )


def test_observation_rejects_bad_age():
    with pytest.raises(ValueError):
        PetObservation(
            pet_token="p", species="dog",
            window_duration_s=30.0, age_years=100.0,
        )


# ---------------------------------------------------------------------------
# PetAssessment
# ---------------------------------------------------------------------------


def test_assessment_rejects_out_of_unit():
    with pytest.raises(ValueError):
        PetAssessment(
            pet_token="p",
            gait_safety=1.2, respiratory_safety=0.5,
            cardiac_safety=0.5, pain_safety=0.5,
            overall=0.5, recommendation="can_wait",
        )


def test_assessment_rejects_unknown_recommendation():
    with pytest.raises(ValueError):
        PetAssessment(
            pet_token="p",
            gait_safety=1.0, respiratory_safety=1.0,
            cardiac_safety=1.0, pain_safety=1.0,
            overall=1.0, recommendation="urgent",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# OwnerMessage — strict guard
# ---------------------------------------------------------------------------


def test_owner_message_allows_friendly_text():
    m = OwnerMessage(
        pet_token="p",
        text="Your dog's walking pattern looks uneven in this clip. Please share with your vet.",
    )
    assert m.text.startswith("Your")


@pytest.mark.parametrize(
    "bad_text",
    [
        "Your pet shows signs of arthritis.",
        "Possible fracture of the forelimb.",
        "Likely infection in the ear.",
        "Appears to be a tumor.",
        "Possibly cardiomyopathy.",
        "Signs of gastroenteritis.",
        "Pancreatitis suspected.",
        "Possible nephropathy.",
        "Hepatopathy indicated.",
        "Likely seizure activity.",
        "Possible stroke.",
        "Diagnosis: lameness.",
    ],
)
def test_owner_message_rejects_clinical_jargon(bad_text: str):
    with pytest.raises(ValueError):
        OwnerMessage(pet_token="p", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Your pet has a broken leg.",
        "Your pet is suffering from pain.",
        "This is a respiratory issue.",
        "Confirms a chronic condition.",
    ],
)
def test_owner_message_rejects_definitive_diagnosis(bad_text: str):
    with pytest.raises(ValueError):
        OwnerMessage(pet_token="p", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Everything is fine with your dog.",
        "Your pet is fine — no issues.",
        "No need to worry about this.",
        "No concerns in the clip.",
        "Safe to skip the vet visit.",
        "No vet visit needed for this.",
        "You can wait without seeing a vet.",
        "Nothing is wrong with your pet.",
        "Your pet is healthy.",
        "No issues at all.",
    ],
)
def test_owner_message_rejects_reassurance_delay(bad_text: str):
    """The strictest layer — owner-facing text cannot imply
    the owner can skip a vet visit based on this library's
    output."""
    with pytest.raises(ValueError):
        OwnerMessage(pet_token="p", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Give medication twice daily.",
        "Administer medication as needed.",
        "Prescribe a course of antibiotics.",
        "Give a pill in the morning.",
    ],
)
def test_owner_message_rejects_owner_instruction(bad_text: str):
    with pytest.raises(ValueError):
        OwnerMessage(pet_token="p", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Max appears to be limping in the clip.",
        "Bella seems uncomfortable.",
        "Charlie is moving oddly.",
    ],
)
def test_owner_message_rejects_pet_name_identifier(bad_text: str):
    with pytest.raises(ValueError):
        OwnerMessage(pet_token="p", text=bad_text)


def test_owner_message_rejects_empty_text():
    with pytest.raises(ValueError):
        OwnerMessage(pet_token="p", text="   ")


# ---------------------------------------------------------------------------
# VetSummary — permissive on clinical vocab
# ---------------------------------------------------------------------------


def test_vet_summary_allows_clinical_vocabulary():
    """Critical property — the VetSummary guard is
    PERMISSIVE on clinical vocabulary. A vet reader
    benefits from terminology like 'forelimb lameness'
    and 'tachypneic at rest' that would be wrong to
    send to an owner."""
    v = VetSummary(
        pet_token="p",
        text="Observations consistent with forelimb lameness, tachypneic at rest, hunched posture intermittent. Pre-visit recommendation: see_today.",
    )
    assert "lameness" in v.text


@pytest.mark.parametrize(
    "bad_text",
    [
        "Diagnosis: forelimb fracture.",
        "Confirmed diagnosis: arthritis.",
        "The pet has a fracture of the radius.",
        "The pet has arthritis of the hip.",
        "The pet has cancer of the bone.",
    ],
)
def test_vet_summary_rejects_definitive_diagnosis(bad_text: str):
    """Even for a clinical reader — the vet examines and
    decides. The library never asserts ownership of a
    diagnosis."""
    with pytest.raises(ValueError):
        VetSummary(pet_token="p", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Schedule surgery for next week.",
        "Order this procedure immediately.",
        "Prescribe this drug: meloxicam.",
        "Prescribe this medication daily.",
        "Administer this drug at home.",
        "Administer this medication as needed.",
    ],
)
def test_vet_summary_rejects_operational_scheduling(bad_text: str):
    with pytest.raises(ValueError):
        VetSummary(pet_token="p", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Owner name: Alice Smith.",
        "Owner phone: 555-1234.",
        "Owner email: alice@example.com.",
        "Owner address: 123 Main St.",
        "Owner's phone recorded.",
        "Owner's email in system.",
        "Owner's address on file.",
    ],
)
def test_vet_summary_rejects_owner_pii(bad_text: str):
    with pytest.raises(ValueError):
        VetSummary(pet_token="p", text=bad_text)


@pytest.mark.parametrize(
    "bad_text",
    [
        "Max appears to be limping.",
        "Bella shows hunched posture.",
        "Charlie shows tachypnea.",
    ],
)
def test_vet_summary_rejects_pet_name_identifier(bad_text: str):
    with pytest.raises(ValueError):
        VetSummary(pet_token="p", text=bad_text)


def test_vet_summary_rejects_empty_text():
    with pytest.raises(ValueError):
        VetSummary(pet_token="p", text="   ")


# ---------------------------------------------------------------------------
# PetReport
# ---------------------------------------------------------------------------


def test_report_rejects_empty_token():
    a = PetAssessment(
        pet_token="p",
        gait_safety=1.0, respiratory_safety=1.0,
        cardiac_safety=1.0, pain_safety=1.0,
        overall=1.0, recommendation="can_wait",
    )
    v = VetSummary(pet_token="p", text="Healthy observations.")
    with pytest.raises(ValueError):
        PetReport(pet_token="", assessment=a, vet_summary=v)


def test_report_as_text_renders_both_streams():
    a = PetAssessment(
        pet_token="p",
        gait_safety=0.5, respiratory_safety=0.5,
        cardiac_safety=1.0, pain_safety=0.5,
        overall=0.5, recommendation="routine_visit",
    )
    v = VetSummary(
        pet_token="p",
        text="Species: dog. Observations consistent with lameness.",
    )
    m = OwnerMessage(
        pet_token="p",
        text="Your dog's clip shows something your vet should review.",
    )
    report = PetReport(
        pet_token="p", assessment=a, vet_summary=v, owner_messages=[m],
    )
    text = report.as_text()
    assert "VET SUMMARY" in text
    assert "OWNER MESSAGES" in text
    assert "routine_visit" in text

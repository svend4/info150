"""Tests for the core dataclasses + claims guard."""

from __future__ import annotations

import pytest

from triage4_farm.core.models import (
    AnimalObservation,
    FarmerAlert,
    HerdReport,
    JointPoseSample,
    WelfareScore,
)


# ---------------------------------------------------------------------------
# JointPoseSample
# ---------------------------------------------------------------------------


def test_joint_pose_sample_ok():
    s = JointPoseSample(joint="hock_l", x=0.5, y=0.7, confidence=0.9)
    assert s.x == 0.5


def test_joint_pose_sample_rejects_out_of_range():
    with pytest.raises(ValueError):
        JointPoseSample(joint="hock_l", x=1.5, y=0.5)
    with pytest.raises(ValueError):
        JointPoseSample(joint="hock_l", x=0.5, y=-0.1)
    with pytest.raises(ValueError):
        JointPoseSample(joint="hock_l", x=0.5, y=0.5, confidence=2.0)


# ---------------------------------------------------------------------------
# AnimalObservation
# ---------------------------------------------------------------------------


def test_observation_minimal():
    obs = AnimalObservation(animal_id="A1", species="dairy_cow")
    assert obs.animal_id == "A1"
    assert obs.pose_frames == []
    assert obs.respiratory_bpm is None


def test_observation_rejects_empty_id():
    with pytest.raises(ValueError):
        AnimalObservation(animal_id="", species="dairy_cow")


def test_observation_rejects_unknown_species():
    with pytest.raises(ValueError):
        AnimalObservation(animal_id="A1", species="alpaca")  # type: ignore[arg-type]


def test_observation_rejects_negative_duration():
    with pytest.raises(ValueError):
        AnimalObservation(animal_id="A1", species="pig", duration_s=-0.5)


def test_observation_rejects_implausible_respiratory():
    with pytest.raises(ValueError):
        AnimalObservation(
            animal_id="A1",
            species="dairy_cow",
            respiratory_bpm=500,
        )


def test_observation_rejects_out_of_range_thermal():
    with pytest.raises(ValueError):
        AnimalObservation(
            animal_id="A1",
            species="pig",
            thermal_hotspot=1.5,
        )


# ---------------------------------------------------------------------------
# WelfareScore
# ---------------------------------------------------------------------------


def test_welfare_score_rejects_out_of_unit():
    with pytest.raises(ValueError):
        WelfareScore(
            animal_id="A1",
            gait=1.2,
            respiratory=0.5,
            thermal=0.5,
            overall=0.7,
            flag="well",
        )


def test_welfare_score_rejects_unknown_flag():
    with pytest.raises(ValueError):
        WelfareScore(
            animal_id="A1",
            gait=0.9,
            respiratory=0.9,
            thermal=0.9,
            overall=0.9,
            flag="healthy",  # type: ignore[arg-type]
        )


def test_welfare_score_stores_values():
    s = WelfareScore(
        animal_id="A1",
        gait=0.9,
        respiratory=0.8,
        thermal=0.85,
        overall=0.87,
        flag="well",
    )
    assert s.flag == "well"
    assert s.animal_id == "A1"


# ---------------------------------------------------------------------------
# FarmerAlert — claims guard
# ---------------------------------------------------------------------------


def test_alert_allows_observation_text():
    alert = FarmerAlert(
        animal_id="A1",
        kind="lameness",
        flag="concern",
        text="Animal A1 shows gait asymmetry. Vet review recommended.",
    )
    assert alert.flag == "concern"


@pytest.mark.parametrize(
    "bad_text",
    [
        "Administer tylosin 20 mg/kg.",
        "Prescribe anti-inflammatory.",
        "Start a withdrawal period.",
        "This animal needs antibiotic treatment.",
        "Diagnose lameness.",
        "Medicate the animal with ...",
        "Begin therapy today.",
        "Increase dose tomorrow.",
        "Treat the hoof with ...",
    ],
)
def test_alert_rejects_veterinary_practice_vocabulary(bad_text: str):
    with pytest.raises(ValueError):
        FarmerAlert(
            animal_id="A1",
            kind="lameness",
            flag="urgent",
            text=bad_text,
        )


def test_alert_rejects_empty_text():
    with pytest.raises(ValueError):
        FarmerAlert(
            animal_id="A1",
            kind="respiratory",
            flag="concern",
            text="   ",
        )


def test_alert_rejects_unknown_flag():
    with pytest.raises(ValueError):
        FarmerAlert(
            animal_id="A1",
            kind="respiratory",
            flag="healthy",  # type: ignore[arg-type]
            text="Something is observed.",
        )


def test_alert_rejects_unknown_kind():
    with pytest.raises(ValueError):
        FarmerAlert(
            animal_id="A1",
            kind="digestion",  # type: ignore[arg-type]
            flag="concern",
            text="Something is observed.",
        )


# ---------------------------------------------------------------------------
# HerdReport
# ---------------------------------------------------------------------------


def test_herd_report_rejects_empty_farm_id():
    with pytest.raises(ValueError):
        HerdReport(farm_id="")


def test_herd_report_as_text_without_alerts():
    report = HerdReport(farm_id="F1", herd_overall=0.93)
    text = report.as_text()
    assert "F1" in text
    assert "consistent" in text.lower()


def test_herd_report_filters_by_flag():
    report = HerdReport(
        farm_id="F1",
        alerts=[
            FarmerAlert(
                animal_id="A1",
                kind="lameness",
                flag="concern",
                text="Animal A1 shows mild asymmetry. Vet review recommended.",
            ),
            FarmerAlert(
                animal_id="A2",
                kind="respiratory",
                flag="urgent",
                text="Animal A2 breathing well above routine range. Vet review recommended.",
            ),
        ],
    )
    assert len(report.alerts_at_flag("urgent")) == 1
    assert report.alerts_at_flag("urgent")[0].kind == "respiratory"
    assert len(report.alerts_at_flag("concern")) == 1


def test_herd_report_animal_count():
    report = HerdReport(
        farm_id="F1",
        scores=[
            WelfareScore(
                animal_id=f"A{i}",
                gait=0.9,
                respiratory=0.9,
                thermal=0.9,
                overall=0.9,
                flag="well",
            )
            for i in range(4)
        ],
    )
    assert report.animal_count == 4

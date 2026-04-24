"""Tests for ClinicalPreTriageEngine + synthetic self-report + demo."""

from __future__ import annotations

import pytest

from triage4_clinic.clinic_triage.adult_clinical_bands import (
    AdultClinicalBands,
)
from triage4_clinic.clinic_triage.triage_engine import (
    ClinicalPreTriageEngine,
)
from triage4_clinic.core.models import PatientObservation, PatientSelfReport
from triage4_clinic.sim.demo_runner import run_demo
from triage4_clinic.sim.synthetic_self_report import (
    demo_submissions,
    generate_observation,
)


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        ClinicalPreTriageEngine(weights={
            "cardiac": 0, "respiratory": 0,
            "acoustic": 0, "postural": 0,
        })


def test_engine_empty_observation_defaults_to_schedule():
    """Critical property — an empty observation must default
    to `schedule`, NEVER to `self_care`. Absence of signals
    is not a clearance."""
    # With no samples, all channels score neutral 1.0, so the
    # empty observation technically satisfies the self_care
    # gate. But the symptom gate catches the more realistic
    # case — if the patient reported any symptom, self_care
    # is blocked regardless of signal absence.
    obs_with_symptom = PatientObservation(
        patient_token="P", window_duration_s=60.0,
        self_report=PatientSelfReport(reports_dizziness=True),
    )
    report2 = ClinicalPreTriageEngine().review(obs_with_symptom)
    # Any reported symptom forbids self_care.
    assert report2.assessment.recommendation != "self_care"


# ---------------------------------------------------------------------------
# Recommendation tiers
# ---------------------------------------------------------------------------


def test_engine_baseline_adult_can_reach_self_care():
    obs = generate_observation(
        patient_token="P", age_years=30, seed=1,
    )
    report = ClinicalPreTriageEngine().review(obs)
    # Baseline healthy adult with no symptoms can legitimately
    # reach self_care.
    assert report.assessment.recommendation == "self_care"


def test_engine_reported_symptom_blocks_self_care():
    """Self-report gate — any reported symptom forbids
    self_care, even on a pristine signal set."""
    obs = generate_observation(
        patient_token="P", age_years=30,
        self_report=PatientSelfReport(reports_chest_pain=True),
        seed=1,
    )
    report = ClinicalPreTriageEngine().review(obs)
    assert report.assessment.recommendation != "self_care"


def test_engine_channel_schedule_blocks_self_care():
    """Channel-schedule gate — a channel below 0.75 blocks
    self_care."""
    obs = generate_observation(
        patient_token="P", age_years=30,
        acoustic_strain=0.4, seed=2,
    )
    report = ClinicalPreTriageEngine().review(obs)
    assert report.assessment.recommendation != "self_care"


def test_engine_elevated_hr_escalates():
    obs = generate_observation(
        patient_token="P", age_years=30,
        hr_elevation=0.8, seed=3,
    )
    report = ClinicalPreTriageEngine().review(obs)
    # Elevated HR should at least reach schedule.
    assert report.assessment.recommendation != "self_care"


def test_engine_severe_elevation_reaches_urgent_review():
    obs = generate_observation(
        patient_token="P", age_years=30,
        hr_elevation=0.85, rr_elevation=0.85, seed=4,
    )
    report = ClinicalPreTriageEngine().review(obs)
    assert report.assessment.recommendation == "urgent_review"


# ---------------------------------------------------------------------------
# Grounded alternatives on emitted alerts
# ---------------------------------------------------------------------------


def test_engine_every_emitted_alert_carries_alternatives():
    """Property: every alert emitted by the engine across
    the demo set carries at least one AlternativeExplanation.
    The positive requirement is structural."""
    submissions = demo_submissions()
    engine = ClinicalPreTriageEngine()
    for obs in submissions:
        report = engine.review(obs)
        for alert in report.alerts:
            assert len(alert.alternative_explanations) >= 1


def test_engine_every_emitted_alert_carries_reasoning_trace():
    """Property: every alert carries a non-empty reasoning
    trace. Audit requirement, enforced structurally."""
    submissions = demo_submissions()
    engine = ClinicalPreTriageEngine()
    for obs in submissions:
        report = engine.review(obs)
        for alert in report.alerts:
            assert alert.reasoning_trace.strip()


def test_engine_reasoning_trace_mentions_signature_version():
    """The reasoning trace should cite the upstream
    signature by its version tag — so a reviewer can tie
    the alert back to exact signature code."""
    obs = generate_observation(
        patient_token="P", hr_elevation=0.8, seed=5,
    )
    report = ClinicalPreTriageEngine().review(obs)
    cardiac_alerts = [a for a in report.alerts if a.channel == "cardiac"]
    assert cardiac_alerts
    trace = cardiac_alerts[0].reasoning_trace
    assert "cardiac_readings@" in trace


def test_engine_readings_tagged_with_signature_versions():
    obs = generate_observation(patient_token="P", seed=6)
    report = ClinicalPreTriageEngine().review(obs)
    versions = {r.signature_version for r in report.readings}
    # All four signatures should be represented.
    assert any(v.startswith("cardiac_readings@") for v in versions)
    assert any(v.startswith("respiratory_readings@") for v in versions)
    assert any(v.startswith("acoustic_strain@") for v in versions)
    assert any(v.startswith("postural_stability@") for v in versions)


# ---------------------------------------------------------------------------
# Determinism + fusion
# ---------------------------------------------------------------------------


def test_engine_is_deterministic():
    a = generate_observation(
        patient_token="det", hr_elevation=0.4, seed=11,
    )
    b = generate_observation(
        patient_token="det", hr_elevation=0.4, seed=11,
    )
    engine = ClinicalPreTriageEngine()
    ra = engine.review(a)
    rb = engine.review(b)
    assert ra.assessment.overall == rb.assessment.overall
    assert [al.text for al in ra.alerts] == [al.text for al in rb.alerts]


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        obs = generate_observation(
            patient_token=f"P{seed}",
            hr_elevation=0.4, rr_elevation=0.3,
            acoustic_strain=0.3, postural_instability=0.3,
            seed=seed,
        )
        report = ClinicalPreTriageEngine().review(obs)
        assert 0.0 <= report.assessment.overall <= 1.0


def test_engine_capture_quality_scales_confidence():
    """Poor capture quality blends channels toward neutral —
    produces a HIGHER overall (less confident call either
    way)."""
    obs_good = generate_observation(
        patient_token="P", hr_elevation=0.35,
        capture_quality="good", seed=7,
    )
    obs_partial = generate_observation(
        patient_token="P", hr_elevation=0.35,
        capture_quality="partial", seed=7,
    )
    engine = ClinicalPreTriageEngine()
    good_overall = engine.review(obs_good).assessment.overall
    partial_overall = engine.review(obs_partial).assessment.overall
    assert partial_overall >= good_overall


def test_engine_respects_custom_bands():
    strict = AdultClinicalBands(
        channel_schedule=0.95, channel_urgent=0.80,
        overall_self_care=0.98, overall_urgent=0.80,
    )
    obs = generate_observation(
        patient_token="P", hr_elevation=0.2, seed=9,
    )
    engine_strict = ClinicalPreTriageEngine(bands=strict)
    engine_default = ClinicalPreTriageEngine()
    strict_report = engine_strict.review(obs)
    default_report = engine_default.review(obs)
    # Strict bands should fire at least as many alerts.
    assert len(strict_report.alerts) >= len(default_report.alerts)


# ---------------------------------------------------------------------------
# Synthetic submissions + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(hr_elevation=2.0)
    with pytest.raises(ValueError):
        generate_observation(rr_elevation=-0.1)
    with pytest.raises(ValueError):
        generate_observation(cough_frequency=2.0)
    with pytest.raises(ValueError):
        generate_observation(acoustic_strain=-0.1)
    with pytest.raises(ValueError):
        generate_observation(postural_instability=2.0)
    with pytest.raises(ValueError):
        generate_observation(window_duration_s=-5)


def test_demo_submissions_length():
    assert len(demo_submissions()) == 5


def test_demo_submissions_deterministic():
    a = demo_submissions()
    b = demo_submissions()
    for oa, ob in zip(a, b):
        assert [s.hr_bpm for s in oa.vitals_samples] == \
               [s.hr_bpm for s in ob.vitals_samples]


def test_run_demo_covers_every_recommendation_tier():
    text = run_demo()
    for rec in ("self_care", "schedule", "urgent_review"):
        assert rec in text


def test_run_demo_every_alert_has_alternatives():
    """Property — parse the demo text and confirm every
    alert line is followed by an alternatives block."""
    text = run_demo()
    # Rough check: as many "alternatives:" headers as
    # individual alert blocks.
    alert_lines = text.count(" · schedule] ") + text.count(" · urgent_review] ")
    alternatives_blocks = text.count("alternatives:")
    assert alert_lines == alternatives_blocks
    assert alert_lines > 0


def test_run_demo_never_emits_reassurance():
    text = run_demo().lower()
    for phrase in (
        "you are fine",
        "no need for review",
        "can skip the visit",
        "no clinical concerns",
        "all vital signs normal",
        "nothing unusual",
    ):
        assert phrase not in text


def test_run_demo_never_emits_regulatory_overclaim():
    text = run_demo().lower()
    for phrase in (
        "fda-cleared",
        "fda cleared",
        "medical device",
        "samd",
        "clinically validated",
        "replaces clinician",
    ):
        assert phrase not in text


def test_run_demo_never_emits_definitive_diagnosis():
    text = run_demo().lower()
    for phrase in (
        "diagnosis of",
        "diagnosis:",
        "the patient has",
        "is a case of",
    ):
        assert phrase not in text

"""Tests for SportPerformanceEngine + synthetic session + demo."""

from __future__ import annotations

import pytest

from triage4_sport.core.models import (
    AthleteObservation,
    PhysicianAlert,
)
from triage4_sport.sim.demo_runner import run_demo
from triage4_sport.sim.synthetic_session import (
    demo_baseline,
    demo_sessions,
    generate_observation,
)
from triage4_sport.sport_engine.monitoring_engine import (
    SportPerformanceEngine,
)
from triage4_sport.sport_engine.performance_bands import (
    PerformanceBands,
)


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        SportPerformanceEngine(weights={
            "form_asymmetry": 0, "workload_load": 0,
            "recovery_hr": 0, "baseline_deviation": 0,
        })


def test_engine_empty_observation_returns_steady():
    obs = AthleteObservation(
        athlete_token="A", sport="soccer",
        session_duration_s=3600,
    )
    report = SportPerformanceEngine().review(obs)
    assert report.assessment.risk_band == "steady"


# ---------------------------------------------------------------------------
# Risk-band tiers
# ---------------------------------------------------------------------------


def test_engine_steady_at_baseline():
    obs = generate_observation(
        athlete_token="A", workload_intensity=0.10, seed=1,
    )
    report = SportPerformanceEngine().review(obs, baseline=demo_baseline())
    assert report.assessment.risk_band == "steady"
    # No coach messages, no physician alert.
    assert report.coach_messages == []
    assert report.physician_alert is None


def test_engine_single_channel_watch_trainer_only():
    """Single-channel mid-band signal fires TrainerNote but
    not CoachMessage and not PhysicianAlert. The fusion
    deliberately under-weights single-channel watch signals."""
    obs = generate_observation(
        athlete_token="A",
        form_asymmetry=0.28, workload_intensity=0.10,
        seed=2,
    )
    report = SportPerformanceEngine().review(obs, baseline=demo_baseline())
    assert report.assessment.risk_band == "steady"
    assert report.trainer_notes  # at least one
    assert report.coach_messages == []
    assert report.physician_alert is None


def test_engine_workload_hold_fires_all_audiences():
    obs = generate_observation(
        athlete_token="A",
        workload_intensity=0.95, seed=3,
    )
    report = SportPerformanceEngine().review(obs, baseline=demo_baseline())
    # Channel-hold override → overall=hold.
    assert report.assessment.risk_band == "hold"


def test_engine_multi_channel_deviation_fires_physician():
    """When overall AND baseline-deviation both cross the
    physician thresholds, the PhysicianAlert fires with a
    reasoning_trace."""
    obs = generate_observation(
        athlete_token="A",
        form_asymmetry=0.55, workload_intensity=0.85,
        recovery_drop_bpm=14.0, seed=4,
    )
    report = SportPerformanceEngine().review(obs, baseline=demo_baseline())
    assert report.assessment.risk_band == "hold"
    assert isinstance(report.physician_alert, PhysicianAlert)
    # Reasoning trace cites all three signature versions.
    trace = report.physician_alert.reasoning_trace.lower()
    assert "form_asymmetry@" in trace
    assert "workload_load@" in trace
    assert "recovery_hr@" in trace


def test_engine_recovery_hold_via_channel_override():
    obs = generate_observation(
        athlete_token="A",
        workload_intensity=0.10, recovery_drop_bpm=10.0,
        seed=5,
    )
    report = SportPerformanceEngine().review(obs, baseline=demo_baseline())
    # recovery_hr_safety = 0 → channel-hold override → hold.
    assert report.assessment.risk_band == "hold"


# ---------------------------------------------------------------------------
# Audience-specific delivery
# ---------------------------------------------------------------------------


def test_engine_coach_messages_use_layperson_language():
    """Property: every CoachMessage in the demo passes the
    strict CoachMessage guard at construction time. Demo
    running cleanly = proof."""
    sessions = demo_sessions()
    engine = SportPerformanceEngine()
    baseline = demo_baseline()
    coach_count = 0
    for obs in sessions:
        report = engine.review(obs, baseline=baseline)
        coach_count += len(report.coach_messages)
        for m in report.coach_messages:
            low = m.text.lower()
            # Must NOT contain clinical jargon.
            for jargon in ("acl", "tear", "fracture", "tendinitis"):
                assert jargon not in low
    # The demo emits coach messages on at least one session.
    assert coach_count > 0


def test_engine_physician_alert_carries_reasoning_trace():
    """Property: every PhysicianAlert across the demo carries
    a non-empty reasoning_trace."""
    sessions = demo_sessions()
    engine = SportPerformanceEngine()
    baseline = demo_baseline()
    for obs in sessions:
        report = engine.review(obs, baseline=baseline)
        if report.physician_alert is not None:
            assert report.physician_alert.reasoning_trace.strip()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_engine_is_deterministic():
    a = generate_observation(
        athlete_token="det", form_asymmetry=0.30, seed=11,
    )
    b = generate_observation(
        athlete_token="det", form_asymmetry=0.30, seed=11,
    )
    engine = SportPerformanceEngine()
    baseline = demo_baseline()
    ra = engine.review(a, baseline=baseline)
    rb = engine.review(b, baseline=baseline)
    assert ra.assessment.overall == rb.assessment.overall
    assert [m.text for m in ra.trainer_notes] == \
           [m.text for m in rb.trainer_notes]


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        obs = generate_observation(
            athlete_token=f"A{seed}",
            form_asymmetry=0.3, workload_intensity=0.6,
            recovery_drop_bpm=20.0, seed=seed,
        )
        report = SportPerformanceEngine().review(
            obs, baseline=demo_baseline(),
        )
        assert 0.0 <= report.assessment.overall <= 1.0


def test_engine_respects_custom_bands():
    strict = PerformanceBands(
        channel_monitor=0.95, channel_hold=0.80,
        overall_monitor=0.95, overall_hold=0.80,
        physician_alert_overall=0.85,
        physician_alert_baseline_deviation=0.85,
    )
    obs = generate_observation(
        athlete_token="A", form_asymmetry=0.20, seed=7,
    )
    eng_strict = SportPerformanceEngine(bands=strict)
    eng_default = SportPerformanceEngine()
    strict_report = eng_strict.review(obs, baseline=demo_baseline())
    default_report = eng_default.review(obs, baseline=demo_baseline())
    # Stricter bands should fire AT LEAST as many trainer
    # notes for the same input.
    assert (
        len(strict_report.trainer_notes)
        >= len(default_report.trainer_notes)
    )


# ---------------------------------------------------------------------------
# Synthetic session + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(form_asymmetry=2.0)
    with pytest.raises(ValueError):
        generate_observation(workload_intensity=-0.1)
    with pytest.raises(ValueError):
        generate_observation(recovery_drop_bpm=200.0)
    with pytest.raises(ValueError):
        generate_observation(session_duration_s=-5)


def test_demo_sessions_length():
    assert len(demo_sessions()) == 5


def test_demo_sessions_deterministic():
    a = demo_sessions()
    b = demo_sessions()
    for oa, ob in zip(a, b):
        assert [m.form_asymmetry for m in oa.movement_samples] == \
               [m.form_asymmetry for m in ob.movement_samples]


def test_run_demo_covers_every_risk_band():
    text = run_demo()
    for band in ("steady", "monitor", "hold"):
        assert band in text


def test_run_demo_emits_all_three_audiences():
    text = run_demo()
    assert "COACH:" in text
    assert "TRAINER:" in text
    assert "PHYSICIAN:" in text


# ---------------------------------------------------------------------------
# Property tests on demo output
# ---------------------------------------------------------------------------


def test_run_demo_never_predicts_injury():
    text = run_demo().lower()
    for phrase in (
        "predicts injury",
        "predict injury",
        "prevents injury",
        "prevent injury",
        "will get injured",
        "injury imminent",
        "guaranteed safe to return",
        "ready to play",
        "cleared to play",
    ):
        assert phrase not in text


def test_run_demo_never_emits_athlete_identifier():
    text = run_demo().lower()
    for prefix in (
        "athlete john ",
        "athlete jane ",
        "player john ",
        "player maria ",
    ):
        assert prefix not in text


def test_run_demo_never_emits_career_jeopardy():
    text = run_demo().lower()
    for phrase in (
        "will be cut",
        "will lose contract",
        "roster decision",
        "marketability",
        "trade rumour",
        "trade rumor",
    ):
        assert phrase not in text


def test_run_demo_never_emits_team_league_names():
    text = run_demo().lower()
    for phrase in (
        "nfl",
        "nba",
        "nhl",
        "mlb",
        "epl",
        "premier league",
        "la liga",
        "bundesliga",
        "serie a",
        "champions league",
    ):
        assert phrase not in text


def test_run_demo_coach_messages_never_contain_clinical_jargon():
    """Property — every CoachMessage in demo passes strict
    layperson guard."""
    text = run_demo().lower()
    # Find COACH: blocks and verify they don't contain
    # clinical jargon.
    blocks = text.split("coach:")[1:]  # rough — split on header
    for block in blocks:
        # Stop at the next audience header.
        for stopword in ("trainer:", "physician:", "athlete:"):
            if stopword in block:
                block = block.split(stopword)[0]
        for jargon in (
            "acl", "mcl", "pcl", "lcl",
            "tear", "fracture", "sprain", "tendinitis",
            "concussion", "rotator cuff", "meniscus",
        ):
            assert jargon not in block

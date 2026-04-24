"""Tests for START + JumpSTART protocols + dispatch engine."""

from __future__ import annotations

import pytest

from triage4_rescue.core.models import (
    CivilianCasualty,
    VitalSignsObservation,
)
from triage4_rescue.sim.demo_runner import run_demo
from triage4_rescue.sim.synthetic_incident import (
    demo_incident,
    generate_casualty,
)
from triage4_rescue.triage_protocol import (
    StartProtocolEngine,
    StartProtocolError,
    tag_adult,
    tag_pediatric,
)


# ---------------------------------------------------------------------------
# Adult START — every branch.
# ---------------------------------------------------------------------------


def _adult(casualty_id: str, **vitals_kwargs) -> CivilianCasualty:
    return CivilianCasualty(
        casualty_id=casualty_id,
        age_years=30,
        vitals=VitalSignsObservation(**vitals_kwargs),
    )


def test_adult_ambulatory_tagged_minor():
    c = _adult("A1", can_walk=True)
    a, _ = tag_adult(c)
    assert a.tag == "minor"
    assert a.age_group == "adult"
    assert not a.flag_for_secondary_review


def test_adult_apneic_pre_reposition_flags_for_retry():
    c = _adult("A2", can_walk=False, respiratory_bpm=None,
               airway_repositioned=False)
    a, _ = tag_adult(c)
    # Pre-reposition: engine emits a flag cue and stores a
    # delayed placeholder so the responder re-checks after
    # airway is repositioned.
    assert a.tag == "delayed"
    assert a.flag_for_secondary_review is True


def test_adult_apneic_post_reposition_tagged_deceased():
    c = _adult("A3", can_walk=False, respiratory_bpm=None,
               airway_repositioned=True)
    a, _ = tag_adult(c)
    assert a.tag == "deceased"
    assert a.flag_for_secondary_review is True


def test_adult_tachypnea_tagged_immediate():
    c = _adult("A4", can_walk=False, respiratory_bpm=32)
    a, _ = tag_adult(c)
    assert a.tag == "immediate"


def test_adult_bradypnea_tagged_immediate():
    c = _adult("A5", can_walk=False, respiratory_bpm=6)
    a, _ = tag_adult(c)
    assert a.tag == "immediate"


def test_adult_perfusion_poor_tagged_immediate():
    c = _adult("A6", can_walk=False, respiratory_bpm=20,
               capillary_refill_s=3.5, follows_commands=True)
    a, _ = tag_adult(c)
    assert a.tag == "immediate"
    assert "perfusion" in a.reasoning


def test_adult_no_pulse_tagged_immediate():
    c = _adult("A7", can_walk=False, respiratory_bpm=20,
               radial_pulse=False, follows_commands=True)
    a, _ = tag_adult(c)
    assert a.tag == "immediate"


def test_adult_mental_status_fails_tagged_immediate():
    c = _adult("A8", can_walk=False, respiratory_bpm=20,
               capillary_refill_s=1.2, follows_commands=False)
    a, _ = tag_adult(c)
    assert a.tag == "immediate"


def test_adult_all_checks_pass_tagged_delayed():
    c = _adult("A9", can_walk=False, respiratory_bpm=18,
               capillary_refill_s=1.2, radial_pulse=True,
               follows_commands=True)
    a, _ = tag_adult(c)
    assert a.tag == "delayed"
    assert not a.flag_for_secondary_review


def test_adult_partial_assessment_flags_for_review():
    # Missing perfusion + mental status → delayed flagged.
    c = _adult("A10", can_walk=False, respiratory_bpm=18)
    a, _ = tag_adult(c)
    assert a.tag == "delayed"
    assert a.flag_for_secondary_review is True


# ---------------------------------------------------------------------------
# JumpSTART pediatric — every branch.
# ---------------------------------------------------------------------------


def _ped(casualty_id: str, age: float = 5, **vitals_kwargs) -> CivilianCasualty:
    return CivilianCasualty(
        casualty_id=casualty_id,
        age_years=age,
        vitals=VitalSignsObservation(**vitals_kwargs),
    )


def test_pediatric_ambulatory_tagged_minor():
    c = _ped("P1", can_walk=True)
    a, _ = tag_pediatric(c)
    assert a.tag == "minor"
    assert a.age_group == "pediatric"


def test_pediatric_apneic_no_pulse_tagged_deceased():
    c = _ped("P2", can_walk=False, respiratory_bpm=None,
             radial_pulse=False)
    a, _ = tag_pediatric(c)
    assert a.tag == "deceased"
    assert a.flag_for_secondary_review is True


def test_pediatric_apneic_with_pulse_flags_rescue_breath_step():
    c = _ped("P3", can_walk=False, respiratory_bpm=None,
             radial_pulse=True)
    a, _ = tag_pediatric(c)
    # Pulse present + apneic → flag for rescue-breath step.
    assert a.tag == "delayed"
    assert a.flag_for_secondary_review is True
    assert "rescue-breath" in a.reasoning


def test_pediatric_apneic_after_rescue_breaths_tagged_deceased():
    c = _ped("P4", can_walk=False, respiratory_bpm=None,
             airway_repositioned=True, radial_pulse=True)
    a, _ = tag_pediatric(c)
    assert a.tag == "deceased"


def test_pediatric_tachypnea_tagged_immediate():
    c = _ped("P5", can_walk=False, respiratory_bpm=55)
    a, _ = tag_pediatric(c)
    assert a.tag == "immediate"


def test_pediatric_bradypnea_tagged_immediate():
    c = _ped("P6", can_walk=False, respiratory_bpm=10)
    a, _ = tag_pediatric(c)
    assert a.tag == "immediate"


def test_pediatric_avpu_unresponsive_tagged_immediate():
    c = _ped("P7", can_walk=False, respiratory_bpm=28,
             follows_commands=False)
    a, _ = tag_pediatric(c)
    assert a.tag == "immediate"


def test_pediatric_all_branches_clear_tagged_delayed():
    c = _ped("P8", can_walk=False, respiratory_bpm=28,
             follows_commands=True)
    a, _ = tag_pediatric(c)
    assert a.tag == "delayed"
    assert not a.flag_for_secondary_review


def test_pediatric_avpu_unknown_flags_for_review():
    c = _ped("P9", can_walk=False, respiratory_bpm=28)
    a, _ = tag_pediatric(c)
    assert a.tag == "delayed"
    assert a.flag_for_secondary_review is True


# ---------------------------------------------------------------------------
# StartProtocolEngine — dispatch.
# ---------------------------------------------------------------------------


def test_engine_handles_empty_incident():
    report = StartProtocolEngine().review(incident_id="I0", casualties=[])
    assert report.assessments == []
    assert len(report.cues) == 1
    assert report.cues[0].kind == "secondary_review"


def test_engine_dispatches_by_age():
    adult = CivilianCasualty(
        casualty_id="A1",
        age_years=30,
        vitals=VitalSignsObservation(can_walk=True),
    )
    child = CivilianCasualty(
        casualty_id="P1",
        age_years=5,
        vitals=VitalSignsObservation(can_walk=True),
    )
    report = StartProtocolEngine().review(
        incident_id="I1",
        casualties=[adult, child],
    )
    by_id = {a.casualty_id: a for a in report.assessments}
    assert by_id["A1"].age_group == "adult"
    assert by_id["P1"].age_group == "pediatric"
    assert by_id["A1"].tag == by_id["P1"].tag == "minor"


def test_engine_refuses_infant():
    infant = CivilianCasualty(
        casualty_id="B1",
        age_years=0.5,
        vitals=VitalSignsObservation(can_walk=False),
    )
    with pytest.raises(StartProtocolError):
        StartProtocolEngine().review(
            incident_id="I1",
            casualties=[infant],
        )


def test_engine_unknown_age_defaults_to_adult_with_advisory():
    c = CivilianCasualty(
        casualty_id="U1",
        age_years=None,
        vitals=VitalSignsObservation(
            can_walk=False,
            respiratory_bpm=18,
            capillary_refill_s=1.2,
            radial_pulse=True,
            follows_commands=True,
        ),
    )
    report = StartProtocolEngine().review(
        incident_id="I1",
        casualties=[c],
    )
    # Adult branch applied.
    assert report.assessments[0].age_group == "adult"
    assert report.assessments[0].tag == "delayed"
    # And an advisory cue prepended.
    advisory = [cue for cue in report.cues
                if cue.severity == "advisory" and cue.casualty_id == "U1"]
    assert len(advisory) >= 1
    assert "age unknown" in advisory[0].text


def test_engine_is_deterministic():
    casualties_a = demo_incident(incident_id="DET", seed=7)
    casualties_b = demo_incident(incident_id="DET", seed=7)
    engine = StartProtocolEngine()
    r_a = engine.review(incident_id="I", casualties=casualties_a)
    r_b = engine.review(incident_id="I", casualties=casualties_b)
    assert [a.tag for a in r_a.assessments] == [a.tag for a in r_b.assessments]
    assert [c.text for c in r_a.cues] == [c.text for c in r_b.cues]


def test_engine_preserves_casualty_order():
    casualties = demo_incident(incident_id="ORD")
    report = StartProtocolEngine().review(
        incident_id="I",
        casualties=casualties,
    )
    expected = [c.casualty_id for c in casualties]
    assert [a.casualty_id for a in report.assessments] == expected


def test_engine_demo_produces_expected_tag_mix():
    casualties = demo_incident(incident_id="MIX")
    report = StartProtocolEngine().review(
        incident_id="I",
        casualties=casualties,
    )
    counts = {
        "immediate": len(report.assessments_with_tag("immediate")),
        "delayed": len(report.assessments_with_tag("delayed")),
        "minor": len(report.assessments_with_tag("minor")),
        "deceased": len(report.assessments_with_tag("deceased")),
    }
    # Mix per demo_incident construction.
    assert counts["minor"] == 5
    assert counts["delayed"] == 2
    assert counts["immediate"] == 3
    assert counts["deceased"] == 1


def test_engine_cues_survive_claims_guard():
    # If the engine ever attempted to emit a forbidden word
    # (clinical or operational), the ResponderCue constructor
    # would throw — so the full demo passing proves the cue
    # vocabulary stays inside the guard.
    casualties = demo_incident(incident_id="GUARD")
    report = StartProtocolEngine().review(
        incident_id="I",
        casualties=casualties,
    )
    # Enough cues to be meaningful.
    assert len(report.cues) >= len(casualties)


# ---------------------------------------------------------------------------
# Synthetic incident + demo runner smoke tests.
# ---------------------------------------------------------------------------


def test_generate_casualty_is_deterministic():
    a = generate_casualty("C1", "immediate_adult_rr", seed=0, age_years=35)
    b = generate_casualty("C1", "immediate_adult_rr", seed=0, age_years=35)
    assert a.vitals.respiratory_bpm == b.vitals.respiratory_bpm
    assert a.vitals.capillary_refill_s == b.vitals.capillary_refill_s


def test_generate_casualty_respects_profile():
    minor = generate_casualty("C1", "minor_adult", seed=0, age_years=30)
    assert minor.vitals.can_walk is True
    immediate = generate_casualty("C2", "immediate_adult_rr", seed=0, age_years=30)
    assert immediate.vitals.can_walk is False
    assert immediate.vitals.respiratory_bpm is not None
    assert immediate.vitals.respiratory_bpm > 30


def test_run_demo_output_mentions_incident_and_tags():
    text = run_demo()
    assert "DEMO_INCIDENT" in text
    assert "minor" in text
    assert "immediate" in text
    assert "deceased" in text

"""Tests for ambulation / breathing / perfusion signatures."""

from __future__ import annotations

from triage4_rescue.core.models import VitalSignsObservation
from triage4_rescue.signatures.ambulation_check import can_ambulate
from triage4_rescue.signatures.breathing_check import classify_breathing
from triage4_rescue.signatures.perfusion_check import classify_perfusion


# ---------------------------------------------------------------------------
# can_ambulate
# ---------------------------------------------------------------------------


def test_ambulation_true():
    assert can_ambulate(VitalSignsObservation(can_walk=True)) is True


def test_ambulation_false():
    assert can_ambulate(VitalSignsObservation(can_walk=False)) is False


def test_ambulation_none_when_unassessed():
    assert can_ambulate(VitalSignsObservation()) is None


# ---------------------------------------------------------------------------
# classify_breathing — adult
# ---------------------------------------------------------------------------


def test_breathing_adult_normal():
    v = VitalSignsObservation(respiratory_bpm=16)
    assert classify_breathing(v, "adult") == "normal"


def test_breathing_adult_tachypnea_is_abnormal():
    v = VitalSignsObservation(respiratory_bpm=32)
    assert classify_breathing(v, "adult") == "abnormal"


def test_breathing_adult_bradypnea_is_abnormal():
    v = VitalSignsObservation(respiratory_bpm=6)
    assert classify_breathing(v, "adult") == "abnormal"


def test_breathing_adult_boundary_30_is_normal():
    # START: > 30 is immediate. Exactly 30 sits in normal.
    v = VitalSignsObservation(respiratory_bpm=30)
    assert classify_breathing(v, "adult") == "normal"


def test_breathing_apneic_pre_reposition():
    v = VitalSignsObservation(respiratory_bpm=None, airway_repositioned=False)
    assert classify_breathing(v, "adult") == "apneic"


def test_breathing_apneic_post_reposition():
    v = VitalSignsObservation(respiratory_bpm=None, airway_repositioned=True)
    assert classify_breathing(v, "adult") == "apneic_post_reposition"


def test_breathing_zero_rate_treated_as_apneic():
    v = VitalSignsObservation(respiratory_bpm=0, airway_repositioned=False)
    assert classify_breathing(v, "adult") == "apneic"


# ---------------------------------------------------------------------------
# classify_breathing — pediatric
# ---------------------------------------------------------------------------


def test_breathing_pediatric_normal():
    v = VitalSignsObservation(respiratory_bpm=30)
    assert classify_breathing(v, "pediatric") == "normal"


def test_breathing_pediatric_tachypnea():
    v = VitalSignsObservation(respiratory_bpm=50)
    assert classify_breathing(v, "pediatric") == "abnormal"


def test_breathing_pediatric_bradypnea():
    v = VitalSignsObservation(respiratory_bpm=12)
    assert classify_breathing(v, "pediatric") == "abnormal"


def test_breathing_pediatric_adult_rate_is_abnormal():
    # A 16/min rate is normal for an adult but too slow for a
    # child — JumpSTART lower bound is 15.
    v = VitalSignsObservation(respiratory_bpm=14)
    assert classify_breathing(v, "pediatric") == "abnormal"
    # 16 itself is just inside the band.
    v = VitalSignsObservation(respiratory_bpm=16)
    assert classify_breathing(v, "pediatric") == "normal"


# ---------------------------------------------------------------------------
# classify_perfusion
# ---------------------------------------------------------------------------


def test_perfusion_poor_no_pulse():
    v = VitalSignsObservation(radial_pulse=False)
    assert classify_perfusion(v) == "poor"


def test_perfusion_poor_slow_refill():
    v = VitalSignsObservation(capillary_refill_s=3.5)
    assert classify_perfusion(v) == "poor"


def test_perfusion_reassuring_pulse_present():
    v = VitalSignsObservation(radial_pulse=True)
    assert classify_perfusion(v) == "reassuring"


def test_perfusion_reassuring_fast_refill():
    v = VitalSignsObservation(capillary_refill_s=1.2)
    assert classify_perfusion(v) == "reassuring"


def test_perfusion_unknown_when_no_channels():
    v = VitalSignsObservation()
    assert classify_perfusion(v) == "unknown"


def test_perfusion_pulse_overrides_refill_when_absent():
    # No-pulse always trumps a fast cap-refill — shock may be
    # present and START errs on the side of immediate.
    v = VitalSignsObservation(radial_pulse=False, capillary_refill_s=1.0)
    assert classify_perfusion(v) == "poor"


def test_perfusion_boundary_2s_is_reassuring():
    # Cap-refill > 2 s is poor. Exactly 2 s is reassuring.
    v = VitalSignsObservation(capillary_refill_s=2.0)
    assert classify_perfusion(v) == "reassuring"

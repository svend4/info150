import pytest

from triage4.evaluation import HMTEvent, HMTReport, evaluate_hmt_lane


def _ev(
    cid: str,
    detected_at: float,
    handoff_at: float,
    sys_priority: str,
    medic_decision: str,
) -> HMTEvent:
    return HMTEvent(
        casualty_id=cid,
        detected_at=detected_at,
        handoff_at=handoff_at,
        system_priority=sys_priority,
        medic_decision=medic_decision,
    )


def test_hmt_empty_returns_zeros():
    r = evaluate_hmt_lane([])
    assert isinstance(r, HMTReport)
    assert r.n_events == 0
    assert r.mean_time_to_handoff_s == 0.0
    assert r.agreement_rate == 0.0


def test_hmt_full_agreement():
    events = [
        _ev("C1", 0.0, 10.0, "immediate", "immediate"),
        _ev("C2", 0.0, 20.0, "delayed", "delayed"),
    ]
    r = evaluate_hmt_lane(events)
    assert r.agreement_rate == 1.0
    assert r.override_rate == 0.0


def test_hmt_override_rate():
    events = [
        _ev("C1", 0.0, 10.0, "immediate", "delayed"),
        _ev("C2", 0.0, 20.0, "delayed", "delayed"),
    ]
    r = evaluate_hmt_lane(events)
    assert r.override_rate == 0.5
    assert r.agreement_rate == 0.5


def test_hmt_mean_and_max_time():
    events = [
        _ev("C1", 0.0, 30.0, "immediate", "immediate"),
        _ev("C2", 10.0, 20.0, "delayed", "delayed"),
    ]
    r = evaluate_hmt_lane(events)
    assert r.mean_time_to_handoff_s == pytest.approx(20.0)
    assert r.max_time_to_handoff_s == pytest.approx(30.0)


def test_hmt_immediate_timeliness_on_time():
    events = [
        _ev("C1", 0.0, 30.0, "immediate", "immediate"),
        _ev("C2", 0.0, 90.0, "immediate", "immediate"),  # over deadline
    ]
    r = evaluate_hmt_lane(events, immediate_deadline_s=60.0)
    assert r.immediate_timeliness_rate == 0.5


def test_hmt_immediate_timeliness_no_immediate_events():
    events = [_ev("C1", 0.0, 10.0, "minimal", "minimal")]
    r = evaluate_hmt_lane(events)
    assert r.immediate_timeliness_rate == 0.0


def test_hmt_rejects_negative_handoff():
    with pytest.raises(ValueError):
        evaluate_hmt_lane(
            [_ev("C1", 10.0, 0.0, "immediate", "immediate")]
        )


def test_hmt_rejects_non_positive_deadline():
    with pytest.raises(ValueError):
        evaluate_hmt_lane([], immediate_deadline_s=0.0)

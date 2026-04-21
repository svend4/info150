import pytest

from triage4.evaluation import Gate2Report, evaluate_gate2


def test_gate2_perfect_accuracy():
    preds = [("C1", "immediate"), ("C2", "minimal")]
    truths = [("C1", "immediate"), ("C2", "minimal")]
    r = evaluate_gate2(preds, truths)
    assert isinstance(r, Gate2Report)
    assert r.accuracy == 1.0
    assert r.critical_miss_rate == 0.0


def test_gate2_critical_miss_counted():
    preds = [("C1", "delayed"), ("C2", "minimal"), ("C3", "immediate")]
    truths = [("C1", "immediate"), ("C2", "immediate"), ("C3", "immediate")]
    r = evaluate_gate2(preds, truths)
    # 2 of 3 truth-immediate cases predicted non-immediate.
    assert r.critical_miss_rate == pytest.approx(2 / 3, abs=1e-3)


def test_gate2_partial_accuracy():
    preds = [("C1", "immediate"), ("C2", "delayed")]
    truths = [("C1", "immediate"), ("C2", "minimal")]
    r = evaluate_gate2(preds, truths)
    assert r.accuracy == 0.5


def test_gate2_unknown_label_ignored():
    preds = [("C1", "immediate")]
    truths = [("C1", "bogus_label")]
    r = evaluate_gate2(preds, truths)
    assert r.accuracy == 0.0


def test_gate2_per_class_f1():
    preds = [("C1", "immediate"), ("C2", "immediate")]
    truths = [("C1", "immediate"), ("C2", "delayed")]
    r = evaluate_gate2(preds, truths)
    assert r.per_class["immediate"].tp == 1
    assert r.per_class["immediate"].fp == 1
    assert r.per_class["delayed"].fn == 1
    assert 0.0 <= r.per_class["immediate"].f1 <= 1.0


def test_gate2_missing_ids_ignored():
    preds = [("C1", "immediate"), ("C_lost", "delayed")]
    truths = [("C1", "immediate")]
    r = evaluate_gate2(preds, truths)
    assert r.accuracy == 1.0


def test_gate2_invalid_critical_class_raises():
    with pytest.raises(ValueError):
        evaluate_gate2([], [], critical_class="not_a_class")


def test_gate2_no_immediate_truth_zero_miss_rate():
    preds = [("C1", "minimal")]
    truths = [("C1", "minimal")]
    r = evaluate_gate2(preds, truths)
    assert r.critical_miss_rate == 0.0

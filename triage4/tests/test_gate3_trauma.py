import pytest

from triage4.evaluation import Gate3Report, evaluate_gate3


def test_gate3_perfect_match():
    preds = {"C1": {"hemorrhage"}, "C2": {"shock_risk", "hemorrhage"}}
    truths = {"C1": {"hemorrhage"}, "C2": {"hemorrhage", "shock_risk"}}
    r = evaluate_gate3(preds, truths)
    assert isinstance(r, Gate3Report)
    assert r.macro_f1 == 1.0
    assert r.micro_f1 == 1.0
    assert r.mean_hamming_accuracy == 1.0


def test_gate3_missed_label_is_fn():
    preds = {"C1": set()}
    truths = {"C1": {"hemorrhage"}}
    r = evaluate_gate3(preds, truths)
    assert r.per_label["hemorrhage"].tp == 0
    assert r.per_label["hemorrhage"].fn == 1


def test_gate3_false_label_is_fp():
    preds = {"C1": {"hemorrhage"}}
    truths = {"C1": set()}
    r = evaluate_gate3(preds, truths)
    assert r.per_label["hemorrhage"].fp == 1


def test_gate3_partial_overlap_reduces_hamming():
    preds = {"C1": {"hemorrhage", "shock_risk"}}
    truths = {"C1": {"hemorrhage"}}
    r = evaluate_gate3(preds, truths)
    # 1 intersect / 2 union = 0.5
    assert r.mean_hamming_accuracy == pytest.approx(0.5)


def test_gate3_empty_inputs():
    r = evaluate_gate3({}, {})
    assert r.macro_f1 == 0.0


def test_gate3_both_empty_sets_is_perfect():
    preds = {"C1": set()}
    truths = {"C1": set()}
    r = evaluate_gate3(preds, truths)
    # No labels predicted nor truthed — score is a perfect agreement.
    assert r.mean_hamming_accuracy == 1.0


def test_gate3_list_input_works():
    preds = {"C1": ["hemorrhage", "shock_risk"]}
    truths = {"C1": ["hemorrhage"]}
    r = evaluate_gate3(preds, truths)
    assert "hemorrhage" in r.per_label
    assert r.per_label["hemorrhage"].tp == 1

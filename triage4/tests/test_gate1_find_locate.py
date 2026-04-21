import pytest

from triage4.evaluation import Gate1Report, evaluate_gate1


def test_gate1_both_empty_is_zero():
    r = evaluate_gate1([], [])
    assert r.tp == 0 and r.fp == 0 and r.fn == 0
    assert r.f1 == 0.0


def test_gate1_perfect_match():
    preds = [("P1", 10.0, 20.0), ("P2", 50.0, 50.0)]
    truths = [("T1", 10.1, 20.1), ("T2", 50.0, 50.0)]
    r = evaluate_gate1(preds, truths, match_distance=1.0)
    assert r.tp == 2
    assert r.fp == 0
    assert r.fn == 0
    assert r.precision == 1.0
    assert r.recall == 1.0
    assert r.f1 == 1.0


def test_gate1_prediction_too_far_is_fp():
    preds = [("P1", 0.0, 0.0)]
    truths = [("T1", 100.0, 100.0)]
    r = evaluate_gate1(preds, truths, match_distance=5.0)
    assert r.tp == 0
    assert r.fp == 1
    assert r.fn == 1


def test_gate1_missed_truth_is_fn():
    preds = [("P1", 0.0, 0.0)]
    truths = [("T1", 0.0, 0.0), ("T2", 20.0, 20.0)]
    r = evaluate_gate1(preds, truths, match_distance=2.0)
    assert r.tp == 1
    assert r.fn == 1


def test_gate1_greedy_nearest_first():
    preds = [("P1", 0.0, 0.0), ("P2", 0.1, 0.0)]
    truths = [("T1", 0.0, 0.0)]
    r = evaluate_gate1(preds, truths, match_distance=1.0)
    # Only one truth — one match, one FP.
    assert r.tp == 1
    assert r.fp == 1
    assert len(r.matched_pairs) == 1


def test_gate1_localization_error_metrics():
    preds = [("P1", 0.0, 0.0), ("P2", 10.0, 0.0)]
    truths = [("T1", 0.5, 0.0), ("T2", 11.0, 0.0)]
    r = evaluate_gate1(preds, truths, match_distance=3.0)
    assert r.tp == 2
    assert r.mean_localization_error > 0.0
    assert r.max_localization_error >= r.mean_localization_error


def test_gate1_rejects_non_positive_distance():
    with pytest.raises(ValueError):
        evaluate_gate1([], [], match_distance=0.0)


def test_gate1_report_dataclass():
    r = evaluate_gate1([("P1", 0.0, 0.0)], [("T1", 0.0, 0.0)])
    assert isinstance(r, Gate1Report)
    assert r.params["match_distance"] == 5.0

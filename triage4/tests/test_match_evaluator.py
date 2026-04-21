import pytest

from triage4.scoring import (
    EvalConfig,
    EvalReport,
    MatchEval,
    aggregate_eval,
    compute_f_score,
    compute_precision,
    compute_recall,
    evaluate_batch_matches,
    evaluate_match,
    filter_eval_by_score,
    rank_matches,
)


def test_eval_config_validates():
    with pytest.raises(ValueError):
        EvalConfig(min_score=-0.1)
    with pytest.raises(ValueError):
        EvalConfig(max_score=0.3, min_score=0.5)
    with pytest.raises(ValueError):
        EvalConfig(beta=0.0)


def test_match_eval_precision_recall_f1():
    ev = MatchEval(pair=(0, 1), score=0.9, tp=8, fp=2, fn=2)
    assert ev.precision == pytest.approx(0.8)
    assert ev.recall == pytest.approx(0.8)
    assert ev.f1 == pytest.approx(0.8)


def test_match_eval_zero_denominator():
    ev = MatchEval(pair=(0, 1), score=0.0, tp=0, fp=0, fn=0)
    assert ev.precision == 0.0
    assert ev.recall == 0.0
    assert ev.f1 == 0.0


def test_compute_precision_recall_basic():
    assert compute_precision(9, 1) == pytest.approx(0.9)
    assert compute_recall(9, 1) == pytest.approx(0.9)
    assert compute_precision(0, 0) == 0.0


def test_compute_f_score_standard_f1():
    # P=R=0.8 → F1 = 0.8
    assert compute_f_score(0.8, 0.8, beta=1.0) == pytest.approx(0.8)


def test_compute_f_score_beta_two_weights_recall():
    # With β>1, recall matters more; if P=0.3 R=0.9, F2 > F1.
    f1 = compute_f_score(0.3, 0.9, beta=1.0)
    f2 = compute_f_score(0.3, 0.9, beta=2.0)
    assert f2 > f1


def test_evaluate_match_builds_obj():
    ev = evaluate_match(pair=(2, 3), score=0.7, tp=5, fp=1, fn=1)
    assert isinstance(ev, MatchEval)
    assert ev.pair == (2, 3)


def test_evaluate_batch_matches_length_mismatch():
    with pytest.raises(ValueError):
        evaluate_batch_matches(
            pairs=[(0, 1)], scores=[0.5], tp_list=[1, 2], fp_list=[0], fn_list=[0]
        )


def test_aggregate_eval_computes_means():
    evals = [
        MatchEval(pair=(0, 1), score=0.6, tp=3, fp=1, fn=1),
        MatchEval(pair=(1, 2), score=0.9, tp=8, fp=2, fn=0),
    ]
    report = aggregate_eval(evals)
    assert isinstance(report, EvalReport)
    assert report.n_pairs == 2
    assert report.mean_score == pytest.approx(0.75)
    assert report.best_pair == (1, 2)


def test_aggregate_eval_empty_returns_zero():
    report = aggregate_eval([])
    assert report.n_pairs == 0
    assert report.best_pair is None
    assert report.best_f1 == 0.0


def test_filter_eval_by_score_strict():
    evals = [
        MatchEval(pair=(0, 1), score=0.3, tp=0, fp=0, fn=0),
        MatchEval(pair=(1, 2), score=0.8, tp=0, fp=0, fn=0),
    ]
    kept = filter_eval_by_score(evals, threshold=0.5)
    assert len(kept) == 1
    assert kept[0].pair == (1, 2)


def test_filter_eval_rejects_negative_threshold():
    with pytest.raises(ValueError):
        filter_eval_by_score([], threshold=-0.1)


def test_rank_matches_by_score_vs_f1():
    evals = [
        MatchEval(pair=(0, 1), score=0.9, tp=1, fp=10, fn=0),  # low f1, high score
        MatchEval(pair=(1, 2), score=0.5, tp=9, fp=1, fn=1),   # high f1, low score
    ]
    by_score = rank_matches(evals, by="score")
    by_f1 = rank_matches(evals, by="f1")
    assert by_score[0].pair == (0, 1)
    assert by_f1[0].pair == (1, 2)


def test_rank_matches_invalid_key():
    with pytest.raises(ValueError):
        rank_matches([], by="foo")

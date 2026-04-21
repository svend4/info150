import numpy as np
import pytest

from triage4.matching import (
    MATCHER_REGISTRY,
    ScoreVector,
    batch_combine,
    compute_scores,
    dtw_distance,
    dtw_distance_mirror,
    get_matcher,
    list_matchers,
    normalize_score_vectors,
    rank_combine,
    register,
    register_fn,
    weighted_combine,
)


# --- DTW --------------------------------------------------------------------


def test_dtw_identical_signals_is_zero():
    a = np.array([[0.0], [0.1], [0.2], [0.1], [0.0]])
    assert dtw_distance(a, a) == pytest.approx(0.0, abs=1e-9)


def test_dtw_shifted_signal_is_small():
    a = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    b = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    assert dtw_distance(a, b, window=3) > 0.0


def test_dtw_handles_1d_input():
    a = [0.0, 0.2, 0.4, 0.2, 0.0]
    b = [0.0, 0.25, 0.4, 0.25, 0.0]
    assert dtw_distance(a, b, window=2) >= 0.0


def test_dtw_mirror_le_direct():
    a = np.array([0.0, 0.1, 0.3, 0.6, 0.9])
    b = np.array([0.9, 0.6, 0.3, 0.1, 0.0])
    direct = dtw_distance(a, b, window=5)
    mirror = dtw_distance_mirror(a, b, window=5)
    assert mirror <= direct


# --- ScoreVector / combiners -------------------------------------------------


def test_score_vector_rejects_out_of_range():
    with pytest.raises(ValueError):
        ScoreVector(idx1=0, idx2=0, scores={"a": 1.5})


def test_weighted_combine_basic():
    sv = ScoreVector(idx1=0, idx2=0, scores={"a": 0.8, "b": 0.4})
    cs = weighted_combine(sv, weights={"a": 3.0, "b": 1.0})
    assert cs.score == pytest.approx((0.8 * 3 + 0.4 * 1) / 4)
    assert set(cs.contributions) == {"a", "b"}


def test_weighted_combine_requires_positive_weight_sum():
    sv = ScoreVector(idx1=0, idx2=0, scores={"a": 0.8})
    with pytest.raises(ValueError):
        weighted_combine(sv, weights={"a": 0.0})


def test_batch_combine_sorts_descending():
    vectors = [
        ScoreVector(idx1=0, idx2=0, scores={"a": 0.3, "b": 0.1}),
        ScoreVector(idx1=1, idx2=0, scores={"a": 0.9, "b": 0.2}),
        ScoreVector(idx1=2, idx2=0, scores={"a": 0.5, "b": 0.8}),
    ]
    results = batch_combine(vectors, method="weighted")
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_normalize_score_vectors():
    vectors = [
        ScoreVector(idx1=0, idx2=0, scores={"a": 0.2}),
        ScoreVector(idx1=1, idx2=0, scores={"a": 0.7}),
    ]
    out = normalize_score_vectors(vectors)
    vals = sorted(v.scores["a"] for v in out)
    assert vals == pytest.approx([0.0, 1.0])


def test_rank_combine_best_gets_one():
    vectors = [
        ScoreVector(idx1=0, idx2=0, scores={"a": 0.9, "b": 0.9}),
        ScoreVector(idx1=1, idx2=0, scores={"a": 0.1, "b": 0.1}),
    ]
    results = rank_combine(vectors)
    by_id = {r.idx1: r.score for r in results}
    assert by_id[0] == pytest.approx(1.0)
    assert by_id[1] == pytest.approx(0.0)


# --- matcher_registry -------------------------------------------------------


def test_register_and_get_matcher():
    MATCHER_REGISTRY.clear()

    @register("dummy_a")
    def dummy_a(x):
        return 0.5

    def dummy_b(x):
        return 0.9

    register_fn("dummy_b", dummy_b)

    assert set(list_matchers()) == {"dummy_a", "dummy_b"}
    assert get_matcher("dummy_a")(None) == 0.5


def test_compute_scores_fails_gracefully():
    MATCHER_REGISTRY.clear()

    @register("good")
    def good(x):
        return 0.5

    @register("bad")
    def bad(x):
        raise RuntimeError("boom")

    scores = compute_scores(None)
    assert scores["good"] == 0.5
    assert scores["bad"] == 0.0


def test_get_matcher_raises_for_unknown():
    MATCHER_REGISTRY.clear()
    with pytest.raises(KeyError):
        get_matcher("nope")

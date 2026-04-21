import numpy as np
import pytest

from triage4.matching import (
    batch_normalize_scores,
    calibrate_scores,
    combine_scores,
    normalize_minmax,
    normalize_rank,
    normalize_score_matrix,
    normalize_zscore,
)


def test_minmax_basic():
    r = normalize_minmax(np.array([1.0, 3.0, 5.0]))
    assert r.scores.tolist() == pytest.approx([0.0, 0.5, 1.0])
    assert r.original_min == 1.0
    assert r.original_max == 5.0


def test_minmax_constant_input_pins_to_low():
    r = normalize_minmax(np.array([2.0, 2.0, 2.0]))
    assert list(r.scores) == pytest.approx([0.0, 0.0, 0.0])


def test_zscore_identical_returns_half():
    r = normalize_zscore(np.array([7.0, 7.0, 7.0]))
    assert list(r.scores) == pytest.approx([0.5, 0.5, 0.5])


def test_zscore_scales_into_unit_interval():
    r = normalize_zscore(np.array([-10.0, 0.0, 10.0]), clip_std=2.0)
    for v in r.scores:
        assert 0.0 <= v <= 1.0


def test_rank_evenly_spaced():
    r = normalize_rank(np.array([10.0, 20.0, 30.0, 40.0]))
    assert r.scores.tolist() == pytest.approx([0.0, 1 / 3, 2 / 3, 1.0])


def test_rank_constant_input():
    r = normalize_rank(np.array([5.0, 5.0, 5.0]))
    assert list(r.scores) == pytest.approx([0.5, 0.5, 0.5])


def test_combine_weighted_average():
    a = np.array([0.0, 1.0])
    b = np.array([1.0, 0.0])
    out = combine_scores([a, b], weights=[1.0, 1.0], method="weighted")
    assert out.tolist() == pytest.approx([0.5, 0.5])


def test_combine_min_max_product():
    a = np.array([0.4, 0.6])
    b = np.array([0.7, 0.1])
    assert combine_scores([a, b], method="min").tolist() == pytest.approx([0.4, 0.1])
    assert combine_scores([a, b], method="max").tolist() == pytest.approx([0.7, 0.6])
    assert combine_scores([a, b], method="product").tolist() == pytest.approx(
        [0.28, 0.06]
    )


def test_combine_rejects_unknown_method():
    with pytest.raises(ValueError):
        combine_scores([np.array([0.0])], method="nonsense")


def test_combine_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        combine_scores([np.array([0.0]), np.array([0.0, 0.0])])


def test_calibrate_scores_shape():
    scores = np.array([0.2, 0.5, 0.8, 0.9])
    reference = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    r = calibrate_scores(scores, reference)
    assert r.scores.shape == scores.shape
    assert r.method == "calibrated"


def test_normalize_score_matrix_preserves_diagonal():
    m = np.array([[1.0, 2.0, 3.0], [2.0, 1.0, 4.0], [3.0, 4.0, 1.0]])
    out = normalize_score_matrix(m, method="minmax", keep_diagonal=True)
    assert out.shape == (3, 3)
    assert np.allclose(np.diag(out), np.diag(m))


def test_batch_normalize_scores_returns_list():
    results = batch_normalize_scores(
        [np.array([0.0, 1.0]), np.array([2.0, 4.0])], method="minmax"
    )
    assert len(results) == 2
    for r in results:
        assert r.method == "minmax"

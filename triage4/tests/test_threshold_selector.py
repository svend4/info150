import numpy as np
import pytest

from triage4.scoring import (
    ThresholdConfig,
    ThresholdResult,
    apply_threshold,
    batch_select_thresholds,
    select_adaptive_threshold,
    select_f1_threshold,
    select_fixed_threshold,
    select_otsu_threshold,
    select_percentile_threshold,
    select_threshold,
)


def test_threshold_config_rejects_bad_method():
    with pytest.raises(ValueError):
        ThresholdConfig(method="wat")


def test_select_fixed_threshold_counts():
    r = select_fixed_threshold(np.array([0.1, 0.5, 0.9]), value=0.5)
    assert isinstance(r, ThresholdResult)
    assert r.threshold == 0.5
    assert r.n_above == 2
    assert r.n_below == 1


def test_select_percentile_matches_numpy():
    arr = np.arange(0.0, 1.01, 0.05)
    r = select_percentile_threshold(arr, percentile=50.0)
    assert r.threshold == pytest.approx(np.percentile(arr, 50.0))


def test_select_otsu_separates_bimodal_scores():
    low = np.random.default_rng(42).normal(0.1, 0.02, 200)
    high = np.random.default_rng(42).normal(0.9, 0.02, 200)
    mix = np.concatenate([low, high])
    r = select_otsu_threshold(mix, n_bins=128)
    assert 0.3 <= r.threshold <= 0.7


def test_select_f1_requires_labels_same_length():
    with pytest.raises(ValueError):
        select_f1_threshold(np.array([0.1, 0.9]), np.array([0]))


def test_select_f1_chooses_useful_threshold():
    scores = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    labels = np.array([0, 0, 0, 1, 1, 1])
    r = select_f1_threshold(scores, labels, n_candidates=20, beta=1.0)
    assert 0.3 <= r.threshold <= 0.8


def test_select_adaptive_is_mid_of_percentile_and_otsu():
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.1, 0.9])
    r = select_adaptive_threshold(scores)
    t_pct = select_percentile_threshold(scores).threshold
    t_otsu = select_otsu_threshold(scores).threshold
    assert r.threshold == pytest.approx((t_pct + t_otsu) / 2.0)


def test_select_threshold_dispatches_by_method():
    scores = np.array([0.1, 0.5, 0.9])
    r = select_threshold(scores, ThresholdConfig(method="fixed", fixed_value=0.4))
    assert r.method == "fixed"
    assert r.threshold == 0.4


def test_select_threshold_f1_without_labels_raises():
    with pytest.raises(ValueError):
        select_threshold(np.array([0.1]), ThresholdConfig(method="f1"))


def test_apply_threshold_returns_bool_mask():
    scores = np.array([0.1, 0.6, 0.9])
    r = select_fixed_threshold(scores, value=0.5)
    mask = apply_threshold(scores, r)
    assert mask.tolist() == [False, True, True]


def test_batch_select_thresholds_returns_list():
    arrays = [np.array([0.1, 0.2, 0.9]), np.array([0.3, 0.5, 0.7])]
    results = batch_select_thresholds(arrays, ThresholdConfig(method="percentile"))
    assert len(results) == 2
    for r in results:
        assert r.method == "percentile"


def test_threshold_result_acceptance_rejection():
    r = ThresholdResult(threshold=0.5, method="fixed", n_above=3, n_below=7, n_total=10)
    assert r.acceptance_ratio == 0.3
    assert r.rejection_ratio == 0.7

    empty = ThresholdResult(threshold=0.5, method="fixed", n_above=0, n_below=0, n_total=0)
    assert empty.acceptance_ratio == 0.0
    assert empty.rejection_ratio == 0.0

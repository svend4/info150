import pytest

from triage4.scoring import (
    FilterCandidatePair,
    FilterConfig,
    FilterReport,
    batch_filter,
    dedup_filter_pairs,
    filter_by_inlier_count,
    filter_by_score_threshold,
    filter_pairs,
    filter_top_k,
    filter_top_k_per_fragment,
    merge_filter_results,
)


def _pair(a: int, b: int, score: float, inliers: int = 0) -> FilterCandidatePair:
    return FilterCandidatePair(id_a=a, id_b=b, score=score, n_inliers=inliers)


def test_filter_config_validation():
    with pytest.raises(ValueError):
        FilterConfig(method="wat")
    with pytest.raises(ValueError):
        FilterConfig(min_score=-0.1)
    with pytest.raises(ValueError):
        FilterConfig(top_k_per_id=0)


def test_candidate_pair_canonical_key():
    p = _pair(5, 2, score=0.9)
    assert p.pair == (2, 5)


def test_filter_by_score_threshold():
    pairs = [_pair(0, 1, 0.3), _pair(1, 2, 0.6), _pair(2, 3, 0.9)]
    out = filter_by_score_threshold(pairs, min_score=0.5)
    assert len(out) == 2


def test_filter_by_inlier_count():
    pairs = [_pair(0, 1, 0.5, inliers=1), _pair(1, 2, 0.5, inliers=10)]
    out = filter_by_inlier_count(pairs, min_inliers=5)
    assert [p.id_b for p in out] == [2]


def test_filter_top_k_descending_score():
    pairs = [_pair(0, 1, 0.2), _pair(1, 2, 0.9), _pair(2, 3, 0.5)]
    out = filter_top_k(pairs, k=2)
    assert [p.score for p in out] == [0.9, 0.5]


def test_dedup_filter_pairs_keeps_best_per_canonical():
    pairs = [_pair(1, 2, 0.4), _pair(2, 1, 0.9)]
    out = dedup_filter_pairs(pairs)
    assert len(out) == 1
    assert out[0].score == 0.9


def test_filter_top_k_per_fragment_caps_per_node():
    pairs = [
        _pair(0, 1, 0.9),
        _pair(0, 2, 0.8),
        _pair(0, 3, 0.7),
        _pair(4, 5, 0.95),
    ]
    out = filter_top_k_per_fragment(pairs, k=1)
    used: set[int] = set()
    for p in out:
        assert p.id_a not in used and p.id_b not in used
        used.add(p.id_a)
        used.add(p.id_b)


def test_filter_pairs_returns_report():
    pairs = [
        _pair(0, 1, 0.3, inliers=2),
        _pair(1, 2, 0.95, inliers=30),
        _pair(2, 3, 0.5, inliers=20),
    ]
    out, report = filter_pairs(
        pairs, FilterConfig(method="combined", min_score=0.5, min_inliers=10)
    )
    assert isinstance(report, FilterReport)
    assert report.n_input == 3
    assert report.n_output == len(out)
    assert 0.0 <= report.rejection_rate <= 1.0


def test_merge_filter_results_dedups_across_lists():
    merged = merge_filter_results(
        [[_pair(0, 1, 0.3)], [_pair(1, 0, 0.9)], [_pair(2, 3, 0.8)]]
    )
    assert len(merged) == 2
    by_pair = {p.pair: p.score for p in merged}
    assert by_pair[(0, 1)] == 0.9


def test_batch_filter_returns_per_input():
    pair_lists = [[_pair(0, 1, 0.5)], [_pair(2, 3, 0.9), _pair(3, 4, 0.1)]]
    results = batch_filter(pair_lists, FilterConfig(min_score=0.3))
    assert len(results) == 2
    for filtered, report in results:
        assert report.n_input >= len(filtered)

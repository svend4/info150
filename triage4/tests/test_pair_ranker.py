import numpy as np
import pytest

from triage4.scoring import (
    RankConfig,
    RankResult,
    RankedPair,
    build_rank_matrix,
    compute_pair_score,
    merge_rank_results,
    rank_pairs_detailed,
)


def test_rank_config_validation():
    with pytest.raises(ValueError):
        RankConfig(top_k=-1)
    with pytest.raises(ValueError):
        RankConfig(min_score=-0.1)
    with pytest.raises(ValueError):
        RankConfig(score_field="bogus")


def test_ranked_pair_validates():
    with pytest.raises(ValueError):
        RankedPair(pair=(0, 1), score=-0.1, rank=1)
    with pytest.raises(ValueError):
        RankedPair(pair=(0, 1), score=0.5, rank=0)


def test_compute_pair_score_weighted_average():
    s = compute_pair_score({"bleeding": 0.8, "motion": 0.4}, {"bleeding": 3.0, "motion": 1.0})
    assert s == pytest.approx((0.8 * 3 + 0.4 * 1) / 4)


def test_compute_pair_score_empty_raises():
    with pytest.raises(ValueError):
        compute_pair_score({})


def test_rank_pairs_detailed_dedup_symmetric():
    pairs = [(0, 1), (1, 0), (0, 2)]
    scores = [0.3, 0.9, 0.5]
    result = rank_pairs_detailed(pairs, scores, RankConfig(deduplicate=True))
    pairs_out = {rp.pair for rp in result.ranked}
    # (0,1) and (1,0) collapse; the higher score 0.9 wins.
    assert (0, 1) in pairs_out
    by_pair = {rp.pair: rp.score for rp in result.ranked}
    assert by_pair[(0, 1)] == pytest.approx(0.9)


def test_rank_pairs_detailed_filters_by_min_score():
    pairs = [(0, 1), (1, 2), (2, 3)]
    scores = [0.1, 0.5, 0.9]
    result = rank_pairs_detailed(pairs, scores, RankConfig(min_score=0.4))
    assert result.n_ranked == 2
    assert result.top_score == pytest.approx(0.9)


def test_rank_pairs_detailed_applies_top_k():
    pairs = [(i, i + 1) for i in range(5)]
    scores = [0.1, 0.2, 0.3, 0.4, 0.5]
    result = rank_pairs_detailed(pairs, scores, RankConfig(top_k=2))
    assert result.n_ranked == 2
    assert [rp.rank for rp in result.ranked] == [1, 2]


def test_rank_result_compression_ratio():
    r = RankResult(
        ranked=[RankedPair(pair=(0, 1), score=0.5, rank=1)],
        n_pairs=10,
        n_ranked=1,
        top_score=0.5,
        mean_score=0.5,
    )
    assert r.compression_ratio == 0.1
    assert r.top_pair == (0, 1)


def test_rank_result_empty_has_no_top_pair():
    r = RankResult(ranked=[], n_pairs=0, n_ranked=0, top_score=0.0, mean_score=0.0)
    assert r.top_pair is None
    assert r.compression_ratio == 0.0


def test_build_rank_matrix_symmetric():
    rp = RankedPair(pair=(0, 1), score=0.9, rank=1)
    result = RankResult(
        ranked=[rp], n_pairs=1, n_ranked=1, top_score=0.9, mean_score=0.9
    )
    mat = build_rank_matrix(result, n_fragments=3)
    assert mat.shape == (3, 3)
    assert mat[0, 1] == mat[1, 0] == 1
    assert np.all(np.diag(mat) == 0)


def test_merge_rank_results_combines_and_reranks():
    r1 = rank_pairs_detailed([(0, 1)], [0.3])
    r2 = rank_pairs_detailed([(1, 2)], [0.9])
    merged = merge_rank_results([r1, r2])
    assert merged.n_ranked == 2
    assert merged.top_score == pytest.approx(0.9)


def test_merge_rank_results_empty_raises():
    with pytest.raises(ValueError):
        merge_rank_results([])

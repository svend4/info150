import numpy as np
import pytest

from triage4.scoring import (
    GlobalRankedPair,
    RankingConfig,
    aggregate_score_matrices,
    batch_global_rank,
    global_rank,
    global_rank_pairs,
    normalize_matrix,
    score_vector,
    top_k_candidates,
)


def _sym(values: list[list[float]]) -> np.ndarray:
    m = np.array(values, dtype=np.float64)
    return (m + m.T) / 2.0


def test_ranking_config_validates():
    with pytest.raises(ValueError):
        RankingConfig(weights={"x": -0.1})
    with pytest.raises(ValueError):
        RankingConfig(top_k=0)
    with pytest.raises(ValueError):
        RankingConfig(min_score=-0.1)


def test_normalize_matrix_scales_off_diagonal():
    m = _sym([[0.0, 0.2, 0.8], [0.2, 0.0, 0.5], [0.8, 0.5, 0.0]])
    n = normalize_matrix(m)
    off = n[~np.eye(3, dtype=bool)]
    assert off.min() == pytest.approx(0.0)
    assert off.max() == pytest.approx(1.0)
    assert np.all(np.diag(n) == 0.0)


def test_normalize_matrix_constant_returns_zeros():
    m = np.ones((3, 3))
    n = normalize_matrix(m)
    assert np.all(n == 0.0)


def test_normalize_matrix_rejects_non_square():
    with pytest.raises(ValueError):
        normalize_matrix(np.zeros((3, 4)))


def test_aggregate_score_matrices_weighted():
    m_a = _sym([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    m_b = _sym([[0.0, 0.0, 1.0], [0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    agg = aggregate_score_matrices(
        {"a": m_a, "b": m_b}, weights={"a": 1.0, "b": 1.0}, normalize=False
    )
    assert agg.shape == (3, 3)
    # (0,1) has a-only → 0.5, (0,2) has b-only → 0.5 after equal weighting.
    assert agg[0, 1] == pytest.approx(0.5)
    assert agg[0, 2] == pytest.approx(0.5)


def test_aggregate_score_matrices_empty_raises():
    with pytest.raises(ValueError):
        aggregate_score_matrices({})


def test_aggregate_score_matrices_shape_mismatch():
    with pytest.raises(ValueError):
        aggregate_score_matrices(
            {"a": np.zeros((3, 3)), "b": np.zeros((4, 4))}
        )


def test_rank_pairs_returns_ordered():
    m = _sym([[0.0, 0.3, 0.9], [0.3, 0.0, 0.5], [0.9, 0.5, 0.0]])
    result = global_rank_pairs(m)
    assert isinstance(result[0], GlobalRankedPair)
    assert [r.score for r in result] == sorted([r.score for r in result], reverse=True)


def test_top_k_candidates_caps_per_fragment():
    m = _sym([
        [0.0, 0.9, 0.8, 0.7],
        [0.9, 0.0, 0.5, 0.4],
        [0.8, 0.5, 0.0, 0.3],
        [0.7, 0.4, 0.3, 0.0],
    ])
    ranked = global_rank_pairs(m)
    top = top_k_candidates(ranked, n_fragments=4, k=2)
    for fid, pairs in top.items():
        assert len(pairs) <= 2


def test_global_rank_end_to_end():
    m_a = _sym([[0.0, 0.9, 0.3], [0.9, 0.0, 0.5], [0.3, 0.5, 0.0]])
    m_b = _sym([[0.0, 0.1, 0.9], [0.1, 0.0, 0.5], [0.9, 0.5, 0.0]])
    result = global_rank({"a": m_a, "b": m_b})
    assert len(result) > 0
    assert all(isinstance(p, GlobalRankedPair) for p in result)


def test_score_vector_aggregates_participation():
    ranked = [
        GlobalRankedPair(idx1=0, idx2=1, score=0.9, rank=0),
        GlobalRankedPair(idx1=1, idx2=2, score=0.5, rank=1),
    ]
    vec = score_vector(ranked, n_fragments=3)
    assert vec.shape == (3,)
    assert vec[0] == pytest.approx(0.9)
    assert vec[1] == pytest.approx((0.9 + 0.5) / 2)


def test_batch_global_rank_returns_per_group():
    m1 = _sym([[0.0, 0.9], [0.9, 0.0]])
    m2 = _sym([[0.0, 0.3], [0.3, 0.0]])
    results = batch_global_rank([{"a": m1}, {"a": m2}])
    assert len(results) == 2

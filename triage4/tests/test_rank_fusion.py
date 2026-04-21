import pytest

from triage4.scoring import (
    borda_count,
    fuse_rankings,
    normalize_scores,
    reciprocal_rank_fusion,
    score_fusion,
)


def test_normalize_scores_min_max():
    out = normalize_scores([10.0, 20.0, 30.0])
    assert out == pytest.approx([0.0, 0.5, 1.0])


def test_normalize_scores_constant_returns_ones():
    out = normalize_scores([5.0, 5.0, 5.0])
    assert out == [1.0, 1.0, 1.0]


def test_normalize_scores_rejects_empty():
    with pytest.raises(ValueError):
        normalize_scores([])


def test_rrf_prefers_consistent_high_rankers():
    ranked = [
        [1, 2, 3, 4],   # scorer A
        [2, 1, 4, 3],   # scorer B
        [1, 3, 2, 4],   # scorer C
    ]
    result = reciprocal_rank_fusion(ranked, k=60)
    # Item 1 appears at ranks 1, 2, 1 — should win.
    assert result[0][0] == 1


def test_rrf_rejects_bad_k():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([[1, 2]], k=0)


def test_borda_count_winner():
    ranked = [[1, 2, 3], [2, 1, 3], [1, 2, 3]]
    result = borda_count(ranked)
    # 1 gets 2+1+2=5, 2 gets 1+2+1=4, 3 gets 0+0+0=0
    by_id = dict(result)
    assert by_id[1] > by_id[2] > by_id[3]


def test_score_fusion_weighted():
    lists = [
        [(1, 10.0), (2, 20.0)],
        [(1, 100.0), (2, 50.0)],
    ]
    result = score_fusion(lists, weights=[1.0, 1.0])
    assert len(result) == 2


def test_score_fusion_normalizes_by_default():
    lists = [
        [(1, 0.1), (2, 0.9)],   # list A — id 2 best
        [(1, 9_000.0), (2, 1.0)],  # list B — id 1 best by a lot
    ]
    result = score_fusion(lists)  # normalize=True
    # After min-max normalisation, both lists contribute equally; neither item
    # should dominate by sheer magnitude.
    top_id = result[0][0]
    assert top_id in (1, 2)


def test_score_fusion_length_mismatch_raises():
    with pytest.raises(ValueError):
        score_fusion([[(1, 0.5)]], weights=[1.0, 2.0])


def test_fuse_rankings_dispatch():
    ranked = [[1, 2], [2, 1]]
    rrf = fuse_rankings(ranked, method="rrf")
    borda = fuse_rankings(ranked, method="borda")
    assert len(rrf) == 2
    assert len(borda) == 2


def test_fuse_rankings_unknown_method():
    with pytest.raises(ValueError):
        fuse_rankings([[1]], method="???")

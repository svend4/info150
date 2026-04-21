import numpy as np
import pytest

from triage4.matching import (
    CandidatePair,
    batch_rank,
    deduplicate_pairs,
    filter_by_score,
    rank_pairs,
    score_pair,
    top_k,
)


def test_score_pair_builds_candidate():
    p = score_pair(3, 7, 0.88, source="handoff")
    assert isinstance(p, CandidatePair)
    assert p.idx1 == 3 and p.idx2 == 7
    assert p.score == pytest.approx(0.88)
    assert p.meta == {"source": "handoff"}


def test_rank_pairs_descending():
    pairs = [score_pair(0, 1, 0.4), score_pair(1, 2, 0.9), score_pair(2, 3, 0.1)]
    ranked = rank_pairs(pairs)
    assert [p.score for p in ranked] == [0.9, 0.4, 0.1]


def test_filter_by_score_strict():
    pairs = [score_pair(0, 1, 0.5), score_pair(1, 2, 0.6), score_pair(2, 3, 0.4)]
    out = filter_by_score(pairs, threshold=0.5)
    assert [p.idx1 for p in out] == [1]


def test_deduplicate_keeps_highest_per_index():
    pairs = [
        score_pair(0, 1, 0.9),
        score_pair(0, 2, 0.8),  # idx 0 already used
        score_pair(3, 4, 0.7),
        score_pair(1, 4, 0.6),  # idx 1 and 4 already used
    ]
    kept = deduplicate_pairs(pairs)
    kept_ids = {(p.idx1, p.idx2) for p in kept}
    assert kept_ids == {(0, 1), (3, 4)}


def test_top_k_with_and_without_dedup():
    pairs = [
        score_pair(0, 1, 0.9),
        score_pair(0, 2, 0.8),
        score_pair(3, 4, 0.7),
    ]
    assert len(top_k(pairs, k=2)) == 2
    # With dedup, (0, 2) collides with (0, 1), so only (0,1) and (3,4) qualify.
    dedup = top_k(pairs, k=3, deduplicate=True)
    assert {(p.idx1, p.idx2) for p in dedup} == {(0, 1), (3, 4)}


def test_batch_rank_on_square_matrix():
    matrix = np.array(
        [
            [0.0, 0.8, 0.2],
            [0.8, 0.0, 0.5],
            [0.2, 0.5, 0.0],
        ]
    )
    pairs = batch_rank(matrix, threshold=0.0, symmetric=True)
    assert [(p.idx1, p.idx2) for p in pairs] == [(0, 1), (1, 2), (0, 2)]
    assert pairs[0].score == pytest.approx(0.8)


def test_batch_rank_rejects_non_square():
    with pytest.raises(ValueError):
        batch_rank(np.zeros((2, 3)))

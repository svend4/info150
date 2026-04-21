import numpy as np
import pytest

from triage4.matching import (
    PairScoreResult,
    ScoringWeights,
    aggregate_channels,
    batch_score_pairs,
    build_score_matrix,
    score_pair_channels,
    select_top_pairs,
)


def test_scoring_weights_validation():
    with pytest.raises(ValueError):
        ScoringWeights(color=-0.1)
    with pytest.raises(ValueError):
        ScoringWeights(color=0.0, texture=0.0, geometry=0.0, gradient=0.0)


def test_scoring_weights_normalized_sum_to_one():
    w = ScoringWeights(color=2.0, texture=1.0, geometry=1.0, gradient=0.0)
    nw = w.normalized()
    assert nw.total == pytest.approx(1.0)


def test_aggregate_channels_uniform_weights():
    s = aggregate_channels({"color": 0.8, "texture": 0.6})
    assert s == pytest.approx(0.7)


def test_aggregate_channels_validates_range():
    with pytest.raises(ValueError):
        aggregate_channels({"color": 1.5})


def test_score_pair_dominant_and_strong():
    r = score_pair_channels(0, 1, {"color": 0.9, "texture": 0.3, "geometry": 0.5, "gradient": 0.1})
    assert isinstance(r, PairScoreResult)
    assert r.dominant_channel == "color"
    assert r.pair_key == (0, 1)
    assert r.n_channels == 4


def test_select_top_pairs_sorts_and_caps():
    rs = [
        score_pair_channels(0, 1, {"color": 0.3}),
        score_pair_channels(0, 2, {"color": 0.9}),
        score_pair_channels(1, 2, {"color": 0.6}),
    ]
    top = select_top_pairs(rs, threshold=0.5, top_k=1)
    assert len(top) == 1
    assert top[0].score == pytest.approx(0.9)


def test_build_score_matrix_is_symmetric():
    rs = [score_pair_channels(0, 1, {"color": 0.8})]
    mat = build_score_matrix(rs, n_fragments=3)
    assert mat.shape == (3, 3)
    assert mat[0, 1] == mat[1, 0]
    assert np.all(np.diag(mat) == 0.0)


def test_batch_score_pairs_length_mismatch_raises():
    with pytest.raises(ValueError):
        batch_score_pairs([(0, 1)], [{"color": 0.5}, {"color": 0.7}])


def test_strong_match_threshold():
    r = score_pair_channels(0, 1, {"color": 0.8, "texture": 0.8})
    assert r.is_strong_match is True
    r2 = score_pair_channels(0, 1, {"color": 0.4, "texture": 0.3})
    assert r2.is_strong_match is False

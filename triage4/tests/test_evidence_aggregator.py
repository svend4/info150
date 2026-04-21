import pytest

from triage4.scoring import (
    EvidenceConfig,
    EvidenceScore,
    aggregate_evidence,
    batch_aggregate,
    compute_confidence,
    rank_by_evidence,
    threshold_evidence,
    weight_evidence,
)


def test_evidence_config_validation():
    with pytest.raises(ValueError):
        EvidenceConfig(min_threshold=2.0)
    with pytest.raises(ValueError):
        EvidenceConfig(confidence_threshold=-0.1)
    with pytest.raises(ValueError):
        EvidenceConfig(weights={"bleeding": -0.5})


def test_threshold_evidence_zeros_weak_signals():
    out = threshold_evidence({"bleeding": 0.2, "motion": 0.9}, min_threshold=0.5)
    assert out == {"bleeding": 0.0, "motion": 0.9}


def test_weight_evidence_basic():
    out = weight_evidence({"bleeding": 0.5}, weights={"bleeding": 2.0})
    assert out == {"bleeding": 1.0}


def test_weight_evidence_defaults_weight_one():
    out = weight_evidence({"posture": 0.7}, weights={})
    assert out == {"posture": 0.7}


def test_weight_evidence_validates_ranges():
    with pytest.raises(ValueError):
        weight_evidence({"bleeding": 1.5}, {})
    with pytest.raises(ValueError):
        weight_evidence({"bleeding": 0.5}, {"bleeding": -1.0})


def test_compute_confidence_empty_is_zero():
    assert compute_confidence({}, {}) == 0.0


def test_compute_confidence_weighted_average():
    weighted = {"bleeding": 0.8, "motion": 0.4}
    weights = {"bleeding": 1.0, "motion": 1.0}
    assert compute_confidence(weighted, weights) == pytest.approx(0.6)


def test_aggregate_evidence_basic():
    cfg = EvidenceConfig(
        weights={"bleeding": 2.0, "motion": 1.0}, min_threshold=0.0
    )
    result = aggregate_evidence({"bleeding": 0.9, "motion": 0.5}, pair_id=(7, 0), cfg=cfg)
    assert isinstance(result, EvidenceScore)
    assert result.pair_id == (7, 0)
    assert 0.0 <= result.confidence <= 1.0
    assert result.n_channels == 2
    assert result.dominant_channel == "bleeding"


def test_aggregate_evidence_require_all_raises():
    cfg = EvidenceConfig(
        weights={"bleeding": 1.0, "motion": 1.0}, require_all=True
    )
    with pytest.raises(ValueError):
        aggregate_evidence({"bleeding": 0.9}, cfg=cfg)


def test_rank_by_evidence_descending():
    scores = [
        EvidenceScore(pair_id=(0, 0), confidence=0.3, n_channels=1),
        EvidenceScore(pair_id=(1, 0), confidence=0.9, n_channels=1),
        EvidenceScore(pair_id=(2, 0), confidence=0.6, n_channels=1),
    ]
    ranked = rank_by_evidence(scores)
    assert [r.pair_id[0] for r in ranked] == [1, 2, 0]


def test_batch_aggregate_defaults_pair_ids():
    cfg = EvidenceConfig(weights={"bleeding": 1.0})
    out = batch_aggregate(
        [{"bleeding": 0.9}, {"bleeding": 0.2}], pair_ids=None, cfg=cfg
    )
    assert len(out) == 2
    assert out[0].pair_id == (0, 1)
    assert out[1].pair_id == (1, 2)


def test_batch_aggregate_length_mismatch_raises():
    with pytest.raises(ValueError):
        batch_aggregate(
            [{"bleeding": 0.5}], pair_ids=[(0, 0), (1, 0)]
        )


def test_is_confident_threshold():
    hi = EvidenceScore(pair_id=(0, 0), confidence=0.8, n_channels=1)
    lo = EvidenceScore(pair_id=(0, 0), confidence=0.3, n_channels=1)
    assert hi.is_confident is True
    assert lo.is_confident is False
